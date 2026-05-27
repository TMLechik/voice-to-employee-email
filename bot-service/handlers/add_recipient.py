from aiogram import F, Router
from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from services import BotService

from .common import (
    edit_or_answer,
    ensure_client,
    ensure_client_from_callback,
    recipient_title,
)
from .keyboards import back_to_menu_keyboard, cancel_add_recipient_keyboard


def get_router(service: BotService) -> Router:
    router = Router(name="add-recipient-command")

    @router.callback_query(F.data == "recipient:add")
    async def ask_recipient_data(callback: CallbackQuery) -> None:
        ensure_client_from_callback(service, callback)
        if not isinstance(callback.message, Message):
            await callback.answer("Не удалось определить текущий чат.", show_alert=True)
            return

        service.cancel_pending_voice_input(callback.from_user.id)
        service.cancel_pending_voice_command(callback.from_user.id)
        service.create_pending_recipient_input(callback.from_user.id, callback.message.chat.id)

        await edit_or_answer(
            callback,
            "Отправьте данные получателя одним сообщением:\n\n"
            "chat_id ФИО получателя\n\n"
            "Например:\n"
            "-1001234567890 Иван Иванов",
            reply_markup=cancel_add_recipient_keyboard(),
        )

    @router.callback_query(F.data == "recipient:add_cancel")
    async def cancel_recipient_input(callback: CallbackQuery) -> None:
        service.cancel_pending_recipient_input(callback.from_user.id)
        await edit_or_answer(
            callback,
            "Добавление получателя отменено.",
            reply_markup=back_to_menu_keyboard(),
        )

    @router.message(PendingRecipientInputFilter(service))
    async def add_recipient_from_message(message: Message) -> None:
        client = ensure_client(service, message)
        text = (message.text or "").strip()

        parsed = _parse_recipient_args(text)
        if parsed is None:
            await message.answer(
                "Не удалось разобрать получателя.\n\n"
                "Отправьте данные в формате:\n"
                "chat_id ФИО получателя",
                reply_markup=cancel_add_recipient_keyboard(),
            )
            return

        chat_id, username, full_name = parsed
        recipient = service.add_recipient(client.id, chat_id, username, full_name)
        service.consume_pending_recipient_input(message.from_user.id, message.chat.id)
        await message.answer(
            "Получатель добавлен:\n"
            f"{recipient_title(recipient)}\n"
            f"chat_id: {recipient.telegram_chat_id}",
            reply_markup=back_to_menu_keyboard(),
        )

    @router.message(PendingRecipientOtherInputFilter(service))
    async def reject_non_text_recipient_input(message: Message) -> None:
        await message.answer(
            "Для добавления получателя отправьте текстом chat_id и ФИО.",
            reply_markup=cancel_add_recipient_keyboard(),
        )

    return router


class PendingRecipientInputFilter(BaseFilter):
    def __init__(self, service: BotService) -> None:
        self.service = service

    async def __call__(self, message: Message) -> bool:
        if message.from_user is None or message.text is None:
            return False
        return self.service.get_pending_recipient_input(
            message.from_user.id,
            message.chat.id,
        ) is not None


class PendingRecipientOtherInputFilter(BaseFilter):
    def __init__(self, service: BotService) -> None:
        self.service = service

    async def __call__(self, message: Message) -> bool:
        if message.from_user is None or message.text is not None:
            return False
        return self.service.get_pending_recipient_input(
            message.from_user.id,
            message.chat.id,
        ) is not None


def _parse_recipient_args(args: str) -> tuple[int, str | None, str] | None:
    parts = args.split(maxsplit=1)
    if len(parts) < 2 or not parts[0].lstrip("-").isdigit():
        return None

    chat_id = int(parts[0])
    full_name = parts[1].strip()
    if not full_name:
        return None

    username = full_name[1:] if full_name.startswith("@") and " " not in full_name else None
    if username:
        full_name = username
    return chat_id, username, full_name
