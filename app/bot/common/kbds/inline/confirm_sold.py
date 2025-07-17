from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

class SoldConfirmCallback(CallbackData, prefix="sold_confirm"):
    action:str
    imei:str
    jan:str
    price:str 


def build_confim_sold_kb(imei, jan, price):
    kb = InlineKeyboardBuilder()
    kb.add(
        InlineKeyboardButton(
            text='Подтвердить',
            callback_data=SoldConfirmCallback(
                action = 'confirm',
                imei=imei,
                jan=jan,
                price=price
            ).pack()
        ),
        InlineKeyboardButton(
            text='Отменить',
            callback_data=SoldConfirmCallback(
                action='cancel',
                imei=imei,
                jan=jan,
                price=price
            ).pack()
        ),
    )
    kb.adjust(1)
    return kb.as_markup()