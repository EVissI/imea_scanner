from contextlib import asynccontextmanager
import os

from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.mongo import MongoStorage
from aiogram.enums import ParseMode
from aiogram.types import Update, Message, Chat, User
from aiogram import Bot, Dispatcher
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import time

from app.bot.middlewares.database_middleware import DatabaseMiddlewareWithCommit, DatabaseMiddlewareWithoutCommit
from app.config import setup_logger

setup_logger("bot")

from loguru import logger
from app.config import settings
from app.bot.routers.setup import setup_router
from app.mongo import mongo_client

storage = MongoStorage(mongo_client.client)

bot = Bot(
    token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    storage=storage
)
admins = settings.ROOT_ADMIN_IDS
dp = Dispatcher(storage=storage)


async def start_bot():
    for admin_id in admins:
        try:
            await bot.send_message(admin_id, f"Я запущен🥳.")
        except:
            pass
    logger.info("Бот успешно запущен.")


async def stop_bot():
    await mongo_client.close()
    try:
        for admin_id in admins:
            await bot.send_message(admin_id, "Бот остановлен. За что?😔")
    except:
        pass
    logger.error("Бот остановлен!")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Бот запущен...")
    await start_bot()
    webhook_url = f"{settings.BASE_URL}/webhook"
    dp.update.middleware.register(DatabaseMiddlewareWithoutCommit())
    dp.update.middleware.register(DatabaseMiddlewareWithCommit())
    dp.include_router(setup_router)
    await bot.set_webhook(
        url=webhook_url,
        allowed_updates=dp.resolve_used_update_types(),
        drop_pending_updates=True,
    )
    logger.success(f"Вебхук установлен: {webhook_url}")
    yield
    logger.info("Бот остановлен...")
    await stop_bot()


app = FastAPI(lifespan=lifespan)


@app.post("/webhook")
async def webhook(request: Request) -> None:
    logger.info("Получен запрос с вебхука.")
    try:
        update_data = await request.json()
        update = Update.model_validate(update_data, context={"bot": bot})
        await dp.feed_update(bot, update)
        logger.info("Обновление успешно обработано.")
    except Exception as e:
        logger.error(f"Ошибка при обработке обновления с вебхука: {e}")


static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
logger.info(f"STATIC DIR: {static_dir}")
app.mount("/static", StaticFiles(directory="app/static"), name="static")


class BarcodeData(BaseModel):
    barcode: str
    chat_id: int


@app.post("/send_barcode")
async def send_barcode(data: BarcodeData):
    fake_update = Update(
        update_id=int(time.time()), 
        message=Message(
            message_id=int(time.time()),
            date=int(time.time()),
            chat=Chat(id=data.chat_id, type="private"),
            from_user=User(id=data.chat_id, is_bot=False, first_name="User"),
            text=data.barcode,
        ),
    )
    await dp.feed_update(bot, fake_update)
    return {"status": "ok"}
