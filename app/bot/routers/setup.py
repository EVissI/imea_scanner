from aiogram import Router
from app.bot.routers.start_router import start_router
from app.bot.routers.checking_invoice import check_invoice_router
from app.bot.routers.add_phones_withot_invoice import add_pair_router
from app.bot.routers.sold_phone import sold_router


setup_router = Router()
setup_router.include_routers(start_router,
                             check_invoice_router,
                             add_pair_router,
                             sold_router
                             )