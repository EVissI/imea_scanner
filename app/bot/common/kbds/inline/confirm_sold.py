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


def create_finish_confirmation_keyboard() -> InlineKeyboardMarkup:
    """
    Создаёт инлайн-клавиатуру с кнопками 'Завершить' и 'Продолжить' для подтверждения завершения сверки.
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Завершить", callback_data="finish_invoice"),
            InlineKeyboardButton(text="Продолжить", callback_data="continue_invoice")
        ]
    ])
    return keyboard


def create_invoice_selection_keyboard(invoices: list) -> InlineKeyboardMarkup:
    """
    Создаёт инлайн-клавиатуру со списком сверек и кнопкой 'Новая сверка'.
    """
    keyboard = [
        [InlineKeyboardButton(
            text=f"Сверка от {invoice['created_at'].strftime('%Y-%m-%d %H:%M')}",
            callback_data=f"select_invoice:{invoice['invoice_id']}"
        )] for invoice in invoices
    ]
    keyboard.append([InlineKeyboardButton(text="Новая сверка", callback_data="new_invoice")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)