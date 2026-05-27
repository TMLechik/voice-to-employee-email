from aiogram import F, Router
from aiogram.types import CallbackQuery

from services import BotService

from .common import MENU_TEXT, edit_or_answer, ensure_client_from_callback
from .keyboards import main_menu_keyboard


def get_router(service: BotService) -> Router:
    router = Router(name="start-command")

    @router.callback_query(F.data == "menu:main")
    async def show_main_menu(callback: CallbackQuery) -> None:
        ensure_client_from_callback(service, callback)
        await edit_or_answer(callback, MENU_TEXT, reply_markup=main_menu_keyboard())

    return router
