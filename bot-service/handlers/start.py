from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from services import BotService

from .common import MENU_TEXT, edit_or_answer, ensure_client, ensure_client_from_callback
from .keyboards import main_menu_keyboard


def get_router(service: BotService) -> Router:
    router = Router(name="start-command")

    @router.message(Command("start"))
    async def start(message: Message) -> None:
        ensure_client(service, message)
        await message.answer(MENU_TEXT, reply_markup=main_menu_keyboard())

    @router.callback_query(F.data == "menu:main")
    async def show_main_menu(callback: CallbackQuery) -> None:
        ensure_client_from_callback(service, callback)
        await edit_or_answer(callback, MENU_TEXT, reply_markup=main_menu_keyboard())

    return router
