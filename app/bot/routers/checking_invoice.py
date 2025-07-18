from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.bot.common.func import is_valid_imei, is_valid_jan, parse_invoice
from app.bot.common.kbds.inline.confirm_sold import create_finish_confirmation_keyboard, create_invoice_selection_keyboard
from app.bot.common.kbds.markup.main_kb import MainKeyboard, create_scanner
from app.db.models import DeviceInfo, RegisteredDevice
from app.db.dao import DeviceInfoDAO, RegisteredDeviceDAO
from app.db.schemas import SDeviceInfo, SRegisteredDevice
from app.mongo import mongo_client
from loguru import logger
from datetime import datetime

check_invoice_router = Router()


class CheckInvoiceStates(StatesGroup):
    invoice = State()
    check = State()
    select_invoice = State()


class AddDeviceStates(StatesGroup):
    device_name = State()


@check_invoice_router.message(F.text == MainKeyboard.get_user_texts()["invoice"])
async def check_invoice(message: Message, state: FSMContext):
    """Проверяет, есть ли активные сверки у пользователя. Если есть — показывает список, если нет — начинает новую."""
    user_id = message.from_user.id
    try:
        invoices = await mongo_client.get_user_invoices(user_id)
    except Exception as e:
        logger.error(f"Ошибка получения сверек для {user_id}: {e}")
        await message.answer("❌ Ошибка при загрузке сверек. Попробуйте позже.")
        return

    if invoices:
        await message.answer(
            "У вас есть незавершённые сверки. Выберите одну или начните новую:",
            reply_markup=create_invoice_selection_keyboard(invoices),
        )
        await state.set_state(CheckInvoiceStates.select_invoice)
    else:
        await message.answer("Пожалуйста, отправьте накладную")
        await state.set_state(CheckInvoiceStates.invoice)


@check_invoice_router.callback_query(F.data == "new_invoice")
async def start_new_invoice(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает нажатие кнопки 'Новая сверка'."""
    await callback.message.answer(
        "Пожалуйста, отправьте накладную для новой сверки",
        reply_markup=MainKeyboard.build_keyboard()
    )
    await state.clear()  
    await state.set_state(CheckInvoiceStates.invoice)
    await callback.message.delete()


@check_invoice_router.callback_query(F.data.startswith("select_invoice:"))
async def select_invoice(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор существующей сверки."""
    user_id = callback.from_user.id
    invoice_id = callback.data.split(":")[1]
    try:
        invoice = await mongo_client.get_invoice_by_id(invoice_id)
    except Exception as e:
        logger.error(f"Ошибка получения сверки {invoice_id}: {e}")
        await callback.message.answer("❌ Ошибка загрузки сверки. Начните новую.")
        await state.clear()
        return

    if not invoice:
        await callback.message.answer(
            "❌ Сверка не найдена. Начните новую.",
            reply_markup=MainKeyboard.build_keyboard()
        )
        await state.clear()
        return

    items = invoice["items"]
    current_index = invoice["current_index"]
    await state.update_data(items=items, current_index=current_index, invoice_text=invoice["invoice_text"], invoice_id=invoice_id)

    if current_index >= len(items):
        await callback.message.answer(
            "✅ Все товары учтены! Сверка завершена.",
            reply_markup=MainKeyboard.build_keyboard()
        )
        await mongo_client.delete_invoice(invoice_id)
        await state.clear()
    else:
        next_name = items[current_index]["item"]["name"]
        await callback.message.answer(
            f"Продолжайте сверку.\nСледующая единица:\n<b>{next_name}</b>\n"
            f"Введите IMEI или JAN для этой позиции.",
            reply_markup=create_scanner(callback.from_user.id),
            parse_mode="HTML",
        )
    await state.set_state(CheckInvoiceStates.check)
    await callback.message.delete()


@check_invoice_router.message(F.text, StateFilter(CheckInvoiceStates.invoice))
async def process_invoice(message: Message, state: FSMContext):
    """Обрабатывает отправку накладной и сохраняет её."""
    if not message.text or len(message.text.strip()) < 10:  # Простая валидация
        await message.answer("❌ Накладная слишком короткая. Проверьте формат.",reply_markup=MainKeyboard.build_keyboard())
        await state.clear()
        return

    try:
        result = parse_invoice(message.text)
    except Exception as e:
        logger.error(f"Ошибка парсинга накладной: {e}")
        await message.answer("❌ Ошибка при парсинге. Проверьте формат.",reply_markup=MainKeyboard.build_keyboard())
        await state.clear()
        return

    if not result["count_ok"] or not result["sum_ok"]:
        await message.answer(
            f"❌ Ошибка!\n"
            f"В накладной указано: {result['invoice_count']} шт., сумма {result['invoice_sum']}\n"
            f"Распознано: {result['parsed_count']} шт., сумма {result['parsed_sum']:.2f}\n"
            f"Проверьте накладную и попробуйте снова.",reply_markup=MainKeyboard.build_keyboard()
        )
        await state.clear()
        return

    items = [{"item": item, "accepted": False, "imei": None, "jan": None} for item in result["items"]]
    invoice_id = await mongo_client.save_invoice(
        user_id=message.from_user.id,
        items=items,
        current_index=0,
        invoice_text=message.text,
        state="check"
    )
    await state.update_data(items=items, current_index=0, invoice_text=message.text, invoice_id=invoice_id)
    await message.answer(
        f"✅ Всё верно!\n"
        f"Позиций: {result['parsed_count']}\n"
        f"Сумма: {result['parsed_sum']:.2f}\n\n"
        f"Теперь отсканируйте или введите IMEI или JAN для:\n<b>{items[0]['item']['name']}</b>",
        reply_markup=create_scanner(message.from_user.id),
        parse_mode="HTML",
    )
    await state.set_state(CheckInvoiceStates.check)


@check_invoice_router.message(F.text == "Закончить сверку", StateFilter(CheckInvoiceStates.check))
async def handle_finish_invoice(message: Message, state: FSMContext):
    """Показывает сводку неучтённых товаров и предлагает подтвердить завершение."""
    data = await state.get_data()
    items = data.get("items", [])
    if not items:
        await message.answer("❌ Нет данных для сверки. Начните заново.", reply_markup=MainKeyboard.build_keyboard())
        await state.clear()
        return

    unaccepted_items = [item["item"]["name"] for item in items if not item["accepted"]]
    if not unaccepted_items:
        await message.answer(
            "✅ Все товары учтены! Вы уверены, что хотите завершить сверку?",
            reply_markup=create_finish_confirmation_keyboard(),
        )
    else:
        unaccepted_text = "\n".join([f"- {name}" for name in unaccepted_items])
        await message.answer(
            f"⚠️ Есть неучтённые товары:\n{unaccepted_text}\n\n"
            f"Вы уверены, что хотите завершить сверку?",
            reply_markup=create_finish_confirmation_keyboard(),
        )


@check_invoice_router.callback_query(F.data == "finish_invoice")
async def confirm_finish_invoice(callback: CallbackQuery, state: FSMContext):
    """Завершает сверку и сохраняет данные."""
    data = await state.get_data()
    invoice_id = data.get("invoice_id")
    items = data.get("items", [])
    current_index = data.get("current_index", 0)

    if not invoice_id:
        logger.warning("invoice_id отсутствует при завершении сверки")
        await callback.message.answer("❌ Ошибка завершения. Начните заново.")
        await state.clear()
        return

    try:
        await mongo_client.update_invoice(invoice_id, items, current_index, state="finished")
    except Exception as e:
        logger.error(f"Ошибка обновления сверки {invoice_id}: {e}")
        await callback.message.answer("❌ Ошибка сохранения. Попробуйте позже.")
        return

    await callback.message.answer(
        "✅ Сверка сохранена. Вы можете вернуться к ней позже.",
        reply_markup=MainKeyboard.build_keyboard()
    )
    await state.clear()
    await callback.message.delete()


@check_invoice_router.callback_query(F.data == "continue_invoice")
async def continue_invoice(callback: CallbackQuery, state: FSMContext):
    """Возвращает к сверке."""
    data = await state.get_data()
    items = data.get("items", [])
    current_index = data.get("current_index", 0)
    invoice_id = data.get("invoice_id")

    if current_index >= len(items):
        await callback.message.answer(
            "✅ Все товары учтены! Сверка завершена.",
            reply_markup=MainKeyboard.build_keyboard()
        )
        if invoice_id:
            await mongo_client.delete_invoice(invoice_id)
        await state.clear()
    else:
        next_name = items[current_index]["item"]["name"]
        await callback.message.answer(
            f"Продолжайте сверку.\nСледующая единица:\n<b>{next_name}</b>\n"
            f"Введите IMEI или JAN для этой позиции.",
            reply_markup=create_scanner(callback.from_user.id),
            parse_mode="HTML",
        )
    await state.set_state(CheckInvoiceStates.check)
    await callback.message.delete()


@check_invoice_router.message(F.text, StateFilter(CheckInvoiceStates.check))
async def accept_unit(message: Message, state: FSMContext, session_without_commit: AsyncSession):
    """Принимает IMEI/JAN и обновляет сверку."""
    data = await state.get_data()
    items = data.get("items", [])
    idx = data.get("current_index", 0)
    invoice_id = data.get("invoice_id")

    if idx >= len(items):
        await message.answer("✅ Все товары учтены! Спасибо.", reply_markup=MainKeyboard.build_keyboard())
        if invoice_id:
            await mongo_client.delete_invoice(invoice_id)
        await state.clear()
        return

    code = message.text.strip()
    if not code or len(code) < 10:  # Простая валидация
        await message.answer("❌ Код слишком короткий. Введите корректный IMEI или JAN.")
        return

    item_name = items[idx]["item"]["name"]
    try:
        async with session_without_commit.begin():  # Транзакция
            if is_valid_imei(code):
                items[idx]["imei"] = code
                imea_exists = await session_without_commit.scalar(
                    select(RegisteredDevice).where(RegisteredDevice.imei == items[idx]["imei"])
                )
                if imea_exists:
                    await message.answer("Этот IMEI уже есть в базе данных, попробуйте другой")
                    return
                await message.answer(f"IMEI принят для:\n<b>{item_name}</b>", parse_mode="HTML")
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
                await message.answer(f"JAN принят для:\n<b>{item_name}</b>", parse_mode="HTML")
            else:
                await message.answer("❌ Не удалось определить тип кода. Введите IMEI или JAN.")
                return

            if items[idx]["imei"] and items[idx]["jan"]:
                await RegisteredDeviceDAO(session_without_commit).add(SRegisteredDevice(
                    imei=items[idx]["imei"],
                    jan=items[idx]["jan"],
                    accepted_by_id=message.from_user.id
                ))
                items[idx]["accepted"] = True
                idx += 1
    except Exception as e:
        logger.error(f"Ошибка транзакции для {item_name}: {e}")
        await message.answer("❌ Ошибка базы данных. Попробуйте позже.")
        return

    if idx < len(items):
        next_name = items[idx]["item"]["name"]
        await message.answer(
            f"Позиция учтена. Следующая единица:\n<b>{next_name}</b>\nВведите IMEI или JAN для этой позиции.",
            reply_markup=create_scanner(message.from_user.id),
            parse_mode="HTML",
        )
    else:
        await message.answer("✅ Все товары учтены! Спасибо.", reply_markup=MainKeyboard.build_keyboard())
        if invoice_id:
            await mongo_client.delete_invoice(invoice_id)
        await state.clear()
    await state.update_data(items=items, current_index=idx, invoice_id=invoice_id)
    if invoice_id:
        await mongo_client.update_invoice(invoice_id, items, idx, state="check")


@check_invoice_router.message(F.text, AddDeviceStates.device_name)
async def add_device_memory(message: Message, state: FSMContext, session_without_commit: AsyncSession):
    """Добавляет устройство, если JAN не найден."""
    data = await state.get_data()
    items = data.get("items", [])
    idx = data.get("current_index", 0)
    invoice_id = data.get("invoice_id")
    jan = items[idx].get("jan")
    device_name = message.text.strip()

    if not device_name or len(device_name) < 2:
        await message.answer("❌ Название устройства слишком короткое. Попробуйте снова.")
        return

    try:
        async with session_without_commit.begin():  # Транзакция
            dao = DeviceInfoDAO(session_without_commit)
            device_schema = SDeviceInfo(jan=jan, device_name=device_name)
            await dao.add(device_schema)
            imei = items[idx].get("imei")
            if imei:
                await RegisteredDeviceDAO(session_without_commit).add(SRegisteredDevice(
                    imei=imei,
                    jan=jan,
                    accepted_by_id=message.from_user.id
                ))
                await message.answer(
                    f"Информация о девайсе с JAN <b>{jan}</b> успешно добавлена!\n"
                    f"Пара IMEI-JAN успешно сохранена!\n\n",
                    parse_mode="HTML",
                )
            else:
                await message.answer(
                    f"Информация о девайсе с JAN <b>{jan}</b> успешно добавлена!\n"
                    f"Введите IMEI для этой пары.",
                    parse_mode="HTML",
                )
    except Exception as e:
        logger.error(f"Ошибка добавления устройства для JAN {jan}: {e}")
        await message.answer("❌ Ошибка базы данных. Попробуйте позже.")
        return

    await state.set_state(CheckInvoiceStates.check)
    if invoice_id:
        await mongo_client.update_invoice(invoice_id, items, idx, state="check")