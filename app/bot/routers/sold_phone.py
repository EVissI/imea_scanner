from sqlalchemy import select
from aiogram import Router,F
from aiogram.filters import StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.common.func import is_valid_imei
from app.bot.common.kbds.inline.confirm_sold import SoldConfirmCallback, build_confim_sold_kb
from app.bot.common.kbds.markup.main_kb import MainKeyboard, create_scanner, create_scanner_sold
from app.db.dao import SoldetDeviceDAO
from app.db.models import RegisteredDevice
from app.db.schemas import SSoldetDevice

sold_router = Router()

class SoldPhoneState(StatesGroup):
    input = State()
    price = State()

@sold_router.message(F.text == MainKeyboard.get_user_texts().get('sold'))
async def start_sold_phone(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Отправьте или отсканируйте IMEI устройства, которое вы хотите продать.\n",
        reply_markup=create_scanner_sold(message.from_user.id)
    )
    await state.set_state(SoldPhoneState.input)

@sold_router.message(F.text == "Закончить сверку", StateFilter(SoldPhoneState.input))
async def back_to_menu(message: Message, state: FSMContext):
    await message.answer(text=message.text, reply_markup=MainKeyboard.build_keyboard())
    await state.clear()

@sold_router.message(F.text, StateFilter(SoldPhoneState.input))
async def input_sold_phone(message: Message, state: FSMContext, session_without_commit: AsyncSession):
    code = message.text.strip()
    if not is_valid_imei(code):
        await message.answer("Пожалуйста, введите или отсканируйте IMEI устройства.")
        return
    imei_exists:RegisteredDevice = await session_without_commit.scalar(
            select(RegisteredDevice).where(RegisteredDevice.imei == code)
        )
    if not imei_exists:
        await state.clear()
        await message.answer('IMEI не был найден в базе данных',reply_markup=MainKeyboard.build_keyboard())
        return
    await message.answer('Введите сумму продажи')
    await state.update_data(imei = code)
    await state.update_data(jan = imei_exists.jan)
    await state.set_state(SoldPhoneState.price)

@sold_router.message(F.text, StateFilter(SoldPhoneState.price))
async def input_sold_phone(message: Message, state: FSMContext, session_without_commit: AsyncSession):
    sold_price = message.text.strip()
    await state.update_data(sold_price = sold_price)
    data = await state.get_data()
    imei = data.get('imei')
    jan = data.get('jan')
    await message.answer(f'IMEI: {imei}\nЦена продажи: {sold_price}',
                        reply_markup=build_confim_sold_kb(imei, 
                                                          jan,
                                                          sold_price))
    await state.clear()

@sold_router.callback_query(SoldConfirmCallback.filter(F.action == 'confirm'))
async def process_confirm(callback:CallbackQuery, callback_data:SoldConfirmCallback, session_with_commit:AsyncSession):
    await callback.message.delete()
    await SoldetDeviceDAO(session_with_commit).add(
        SSoldetDevice(
            imei=callback_data.imei,
            jan=callback_data.jan,
            sale_price=callback_data.price,
            sold_by_id=callback.from_user.id
        )
    )
    await callback.message.answer('Продажа добавлена',reply_markup=MainKeyboard.build_keyboard())

@sold_router.callback_query(SoldConfirmCallback.filter(F.action == 'cancel'))
async def process_cancel(callback:CallbackQuery):
    await callback.message.delete()
    await callback.message.answer('Продажа отменена',reply_markup=MainKeyboard.build_keyboard())