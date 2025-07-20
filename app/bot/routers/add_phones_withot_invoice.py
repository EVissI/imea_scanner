from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.types import Message
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.bot.common.func import is_valid_imei, is_valid_barcode
from app.bot.common.kbds.markup.main_kb import MainKeyboard, create_scanner
from app.db.models import DeviceInfo, RegisteredDevice
from app.db.dao import DeviceInfoDAO, RegisteredDeviceDAO
from app.db.schemas import SDeviceInfo, SRegisteredDevice

add_pair_router = Router()

class InputKeysState(StatesGroup):
    input = State()

class AddJanInfoState(StatesGroup):
    device_name = State()

@add_pair_router.message(F.text == MainKeyboard.get_user_texts().get('add_phone'))
async def start_add_pair(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Отправьте или отсканируйте IMEI или JAN устройства.\n"
        "Для завершения нажмите 'Закончить сверку'.",
        reply_markup=create_scanner(message.from_user.id)
    )
    await state.set_state(InputKeysState.input)

@add_pair_router.message(F.text == "Закончить сверку", StateFilter(InputKeysState.input))
async def finish_add_pair(message: Message, state: FSMContext, session_without_commit: AsyncSession):
    await message.answer(text = message.text, reply_markup = MainKeyboard.build_keyboard())
    await state.clear()

@add_pair_router.message(F.text, StateFilter(InputKeysState.input))
async def input_keys(message: Message, state: FSMContext, session_without_commit: AsyncSession):
    code = message.text.strip()
    data = await state.get_data()
    current = data.get("current", {})

    if is_valid_imei(code):
        current["imei"] = code
        imea_exists = await session_without_commit.scalar(
            select(RegisteredDevice).where(RegisteredDevice.imei == current["imei"])
        )
        if imea_exists:
            await message.answer('Этот IMEI уже есть в базе данных, попробуйте другой')
            return
    elif is_valid_barcode(code):
        current["jan"] = code
        jan_exists = await session_without_commit.scalar(
            select(DeviceInfo).where(DeviceInfo.jan == current["jan"])
        )
        if not jan_exists:
            await state.update_data(current=current)
            await message.answer(
                f"JAN <b>{current['jan']}</b> не найден в базе.\nПожалуйста, введите название устройства:",
                reply_markup=create_scanner(message.from_user.id),
                parse_mode="HTML"
            )
            await state.set_state(AddJanInfoState.device_name)
            return
    else:
        await message.answer(
            "❌ Не удалось определить тип кода.",
            reply_markup=create_scanner(message.from_user.id)
        )
        return

    if current.get("imei") and current.get("jan"):
        await RegisteredDeviceDAO(session_without_commit).add(SRegisteredDevice(
            imei=current.get("imei"), 
            jan=current.get("jan"), 
            accepted_by_id=message.from_user.id))
        await session_without_commit.commit()
        await message.answer(
            f"Пара IMEI-JAN успешно сохранена!\n\n"
            "Отправьте или отсканируйте IMEI или JAN следующего устройства, либо нажмите 'Закончить сверку'.",
            reply_markup=create_scanner(message.from_user.id),
            parse_mode="HTML"
        )
    else:
        await state.update_data(current=current)
        await message.answer(
            "Теперь отправьте второй код (IMEI или JAN) для этой пары.",
            reply_markup=create_scanner(message.from_user.id)
        )


@add_pair_router.message(F.text, StateFilter(AddJanInfoState.device_name))
async def add_jan_country(message: Message, state: FSMContext, session_without_commit: AsyncSession):
    data = await state.get_data()
    current = data.get("current", {})
    dao = DeviceInfoDAO(session_without_commit)
    device_schema = SDeviceInfo(
        jan=current.get("jan"),
        device_name=message.text.strip(),
    )
    await dao.add(device_schema)
    if current.get("imei"):
        await RegisteredDeviceDAO(session_without_commit).add(SRegisteredDevice(
            imei=current.get("imei"), 
            jan=current.get("jan"), 
            accepted_by_id=message.from_user.id))
        await message.answer(
            f"Устройство с JAN <b>{current.get('jan')}</b> и пара IMEI-JAN успешно сохранены!\n\n"
            "Отправьте или отсканируйте IMEI или JAN следующего устройства, либо нажмите 'Закончить сверку'.",
            reply_markup=create_scanner(message.from_user.id),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "Теперь отправьте второй код (IMEI или JAN) для этой пары.",
            reply_markup=create_scanner(message.from_user.id)
        )
    await session_without_commit.commit()
    await state.set_state(InputKeysState.input)
    