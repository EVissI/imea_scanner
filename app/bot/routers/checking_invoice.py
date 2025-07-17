from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.bot.common.func import is_valid_imei, is_valid_jan, parse_invoice, pop_first
from app.bot.common.kbds.markup.main_kb import MainKeyboard, create_scanner
from app.db.models import DeviceInfo, RegisteredDevice
from app.db.dao import DeviceInfoDAO, RegisteredDeviceDAO
from app.db.schemas import SDeviceInfo, SRegisteredDevice

check_invoice_router = Router()


class CheckInvoiceStates(StatesGroup):
    invoice = State()
    check = State()


class AddDeviceStates(StatesGroup):
    device_name = State()


@check_invoice_router.message(F.text == MainKeyboard.get_user_texts()["invoice"])
async def check_invoice(message: Message, state: FSMContext):
    await message.answer(
        "Пожалуйста, отправьте накладную",
    )
    await state.set_state(CheckInvoiceStates.invoice)


@check_invoice_router.message(F.text, StateFilter(CheckInvoiceStates.invoice))
async def process_invoice(message: Message, state: FSMContext):
    result = parse_invoice(message.text)
    print(result)
    if not result["count_ok"] or not result["sum_ok"]:
        await message.answer(
            f"❌ Ошибка!\n"
            f"В накладной указано: {result['invoice_count']} шт., сумма {result['invoice_sum']}\n"
            f"Распознано: {result['parsed_count']} шт., сумма {result['parsed_sum']:.2f}\n"
            f"Проверьте накладную и попробуйте снова."
        )
        await state.clear()
        return

    items = [
        {"item": item, "accepted": False, "imei": None, "jan": None}
        for item in result["items"]
    ]
    await state.update_data(items=items, current_index=0)
    await message.answer(
        f"✅ Всё верно!\n"
        f"Позиций: {result['parsed_count']}\n"
        f"Сумма: {result['parsed_sum']:.2f}\n\n"
        f"Теперь отсканируйте или введите IMEI или JAN для:\n<b>{items[0]['item']['name']}</b>",
        reply_markup=create_scanner(message.from_user.id),
        parse_mode="HTML",
    )
    await state.set_state(CheckInvoiceStates.check)


@check_invoice_router.message(F.text, StateFilter(CheckInvoiceStates.check))
async def accept_unit(
    message: Message, state: FSMContext, session_without_commit: AsyncSession
):
    data = await state.get_data()
    items = data.get("items", [])
    idx = data.get("current_index", 0)

    if idx >= len(items):
        await message.answer("✅ Все товары учтены! Спасибо.")
        await state.clear()
        return

    code = message.text.strip()
    item_name = items[idx]["item"]["name"]

    if is_valid_imei(code):
        items[idx]["imei"] = code
        imea_exists = await session_without_commit.scalar(
            select(RegisteredDevice).where(RegisteredDevice.imei == items[idx]["imei"])
        )
        if imea_exists:
            await message.answer('Этот IMEI уже есть в базе данных, попробуйте другой')
            return
        await message.answer(
            f"IMEI принят для:\n<b>{item_name}</b>",
            parse_mode="HTML",
        )
    elif is_valid_jan(code):
        jan_exists = await session_without_commit.scalar(
            select(DeviceInfo).where(DeviceInfo.jan == code)
        )
        items[idx]["jan"] = code
        if not jan_exists:
            await message.answer(
                f"JAN <b>{code}</b> не найден в базе.\nПожалуйста, введите название устройства:",
                parse_mode="HTML",
            )
            await state.set_state(AddDeviceStates.device_name)
            return
        await message.answer(
            f"JAN принят для:\n<b>{item_name}</b>",
            parse_mode="HTML",
        )
    else:
        await message.answer("❌ Не удалось определить тип кода. Введите IMEI или JAN.")
        return

    if items[idx]["imei"] and items[idx]["jan"]:
        await RegisteredDeviceDAO(session_without_commit).add(SRegisteredDevice(
            imei=items[idx]["imei"], 
            jan=items[idx]["jan"],
            accepted_by_id=message.from_user.id))
        items[idx]["accepted"] = True
        await session_without_commit.commit()
        idx = idx +1
        print(idx)
        print(len(items))
        if idx < len(items):
            next_name = items[idx]["item"]["name"]
            await message.answer(
                f"Позиция учтена. Следующая единица:\n"
                f"<b>{next_name}</b>\nВведите IMEI или JAN для этой позиции.",
                parse_mode="HTML",
            )
        else:
            await message.answer("✅ Все товары учтены! Спасибо.",reply_markup=MainKeyboard.build_keyboard())
            await state.clear()
            return
    await state.update_data(items=items, current_index=idx)


@check_invoice_router.message(F.text, AddDeviceStates.device_name)
async def add_device_memory(message: Message, state: FSMContext,session_without_commit: AsyncSession):
    data = await state.get_data()
    items = data.get("items", [])
    idx = data.get("current_index", 0)
    jan = items[idx].get("jan")
    device_name = message.text.strip()
    imei = items[idx].get("imei")
    dao = DeviceInfoDAO(
        session_without_commit
    )  
    device_schema = SDeviceInfo(
        jan=jan, device_name=device_name
    )
    await dao.add(device_schema)
    if imei:
        await RegisteredDeviceDAO(session_without_commit).add(SRegisteredDevice(
            imei=imei, 
            jan=jan, 
            accepted_by_id=message.from_user.id))
        await message.answer(
            f"Информация о девайсе с JAN <b>{jan}</b> успешно добавлена!\n"
            f"Пара IMEI-JAN успешно сохранена!\n\n",
            parse_mode="HTML",
        )
    else:
        await message.answer(
            f"Информация о девайсе с JAN <b>{jan}</b> успешно добавлена!\n"
            "Введите IMEI для этой пары.",
            parse_mode="HTML",
        )
    await session_without_commit.commit()
    await state.set_state(CheckInvoiceStates.check)

