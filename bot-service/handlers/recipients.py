from aiogram import F, Router
from aiogram.types import CallbackQuery

from services import BotService

from .common import edit_or_answer, ensure_client_from_callback, format_recipients
from .keyboards import empty_recipients_keyboard, recipients_list_keyboard


def get_router(service: BotService) -> Router:
    router = Router(name="recipients-command")

    @router.callback_query(F.data == "menu:recipients")
    async def recipients_callback(callback: CallbackQuery) -> None:
        client = ensure_client_from_callback(service, callback)
        linked_recipients = service.list_recipients(client.id)
        reply_markup = (
            recipients_list_keyboard()
            if linked_recipients
            else empty_recipients_keyboard()
        )
        await edit_or_answer(
            callback,
            format_recipients(linked_recipients),
            reply_markup=reply_markup,
        )

    return router
