from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from services import BotService

from .common import edit_or_answer, ensure_client_from_callback
from .keyboards import back_to_menu_keyboard


def get_router(service: BotService) -> Router:
    router = Router(name="id-command")

    @router.callback_query(F.data == "menu:id")
    async def show_ids_callback(callback: CallbackQuery) -> None:
        ensure_client_from_callback(service, callback)
        chat_id = callback.message.chat.id if isinstance(callback.message, Message) else "unknown"
        chat_type = callback.message.chat.type if isinstance(callback.message, Message) else "unknown"
        await edit_or_answer(
            callback,
            "Идентификаторы Telegram:\n"
            f"user_id: {callback.from_user.id}\n"
            f"chat_id: {chat_id}\n"
            f"chat_type: {chat_type}",
            reply_markup=back_to_menu_keyboard(),
        )

    return router
