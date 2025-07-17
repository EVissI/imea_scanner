from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from app.config import settings

def create_scanner(user_id: int) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.add(
        KeyboardButton(
            text="Сканировать штрихкод",
            web_app=WebAppInfo(url=f"{settings.BASE_URL}/static/barcode_scanner.html?chat_id={user_id}&base_url={settings.BASE_URL}")
        ),
    )
    builder.add(
        KeyboardButton(
            text="Закончить сверку",
        )
    )
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)

def create_scanner_sold(user_id: int) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.add(
        KeyboardButton(
            text="Сканировать штрихкод",
            web_app=WebAppInfo(url=f"{settings.BASE_URL}/static/barcode_scanner.html?chat_id={user_id}&base_url={settings.BASE_URL}")
            # web_app=WebAppInfo(url=f"{settings.BASE_URL}/static/barcode_scanner.html?chat_id={user_id}&base_url={settings.BASE_URL}")
        ),
    )
    builder.add(
        KeyboardButton(
            text="Назад в меню",
        )
    )
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)

class MainKeyboard:
    user_kbd_text = {
        'invoice': 'Загрузить накладную',
        'add_phone': 'Добавить ТМЦ',
        'sold': 'Продать устройство',
    }
    @staticmethod
    def get_user_texts():
        return MainKeyboard.user_kbd_text
    
    @staticmethod
    def build_keyboard() -> ReplyKeyboardMarkup:
        builder = ReplyKeyboardBuilder()
        for text in MainKeyboard.user_kbd_text.values():
            builder.add(
                KeyboardButton(
                    text=text,
                )
            )
        return builder.as_markup(resize_keyboard=True)
