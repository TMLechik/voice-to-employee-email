from aiogram import F, Router
from aiogram.types import Message

from services import BotService

from .common import MENU_TEXT, ensure_client
from .keyboards import main_menu_keyboard


def get_router(service: BotService) -> Router:
    router = Router(name="fallback")

    @router.message(F.chat.type == "private")
    async def fallback(message: Message) -> None:
        ensure_client(service, message)
        await message.answer(MENU_TEXT, reply_markup=main_menu_keyboard())

    return router
