from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from services import BotService

from .common import HELP_TEXT, edit_or_answer, ensure_client, ensure_client_from_callback
from .keyboards import back_to_menu_keyboard


def get_router(service: BotService) -> Router:
    router = Router(name="help-command")

    @router.message(Command("help"))
    async def help_command(message: Message) -> None:
        ensure_client(service, message)
        await message.answer(HELP_TEXT, reply_markup=back_to_menu_keyboard())

    @router.callback_query(F.data == "menu:help")
    async def help_callback(callback: CallbackQuery) -> None:
        ensure_client_from_callback(service, callback)
        await edit_or_answer(callback, HELP_TEXT, reply_markup=back_to_menu_keyboard())

    return router
