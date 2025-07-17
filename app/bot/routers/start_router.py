from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from app.bot.common.kbds.markup.main_kb import MainKeyboard
from app.db.dao import UserDAO
from app.db.schemas import SUser

start_router = Router() 


@start_router.message(CommandStart())
async def start_command(message: Message, session_with_commit: AsyncSession):
    user_data = message.from_user
    user_id = user_data.id
    user_info = await UserDAO(session_with_commit).find_one_or_none_by_id(user_id)
    if user_info is None:
        user_schema = SUser(id=user_id, first_name=user_data.first_name,
                            last_name=user_data.last_name, username=user_data.username)
        await UserDAO(session_with_commit).add(user_schema)
    await message.answer(
        "Привет! Я бот",reply_markup=MainKeyboard.build_keyboard()
    )
