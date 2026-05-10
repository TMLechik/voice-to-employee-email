from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

from services import BotService

from .common import (
    chat_full_name,
    chat_username,
    edit_or_answer,
    ensure_client,
    ensure_client_from_callback,
    recipient_title,
)
from .keyboards import back_to_menu_keyboard


def get_router(service: BotService) -> Router:
    router = Router(name="add-recipient-command")

    @router.message(Command("add_recipient"))
    async def add_recipient(message: Message, command: CommandObject) -> None:
        client = ensure_client(service, message)
        args = (command.args or "").strip()

        if args:
            parsed = _parse_recipient_args(args)
            if parsed is None:
                await message.answer(
                    "Не удалось разобрать получателя. Используйте:\n"
                    "/add_recipient <chat_id> <название>",
                    reply_markup=back_to_menu_keyboard(),
                )
                return
            chat_id, username, full_name = parsed
        else:
            chat_id = message.chat.id
            username = chat_username(message)
            full_name = chat_full_name(message)

        recipient = service.add_recipient(client.id, chat_id, username, full_name)
        await message.answer(
            "Получатель добавлен:\n"
            f"{recipient_title(recipient)}\n"
            f"chat_id: {recipient.telegram_chat_id}",
            reply_markup=back_to_menu_keyboard(),
        )

    @router.callback_query(F.data == "recipient:add_current")
    async def add_current_chat(callback: CallbackQuery) -> None:
        client = ensure_client_from_callback(service, callback)
        if not isinstance(callback.message, Message):
            await callback.answer("Не удалось определить текущий чат.", show_alert=True)
            return

        recipient = service.add_recipient(
            client_id=client.id,
            telegram_chat_id=callback.message.chat.id,
            username=chat_username(callback.message),
            full_name=chat_full_name(callback.message),
        )
        await edit_or_answer(
            callback,
            "Получатель добавлен:\n"
            f"{recipient_title(recipient)}\n"
            f"chat_id: {recipient.telegram_chat_id}",
            reply_markup=back_to_menu_keyboard(),
        )

    return router


def _parse_recipient_args(args: str) -> tuple[int, str | None, str] | None:
    parts = args.split(maxsplit=1)
    if not parts or not parts[0].lstrip("-").isdigit():
        return None

    chat_id = int(parts[0])
    full_name = parts[1].strip() if len(parts) > 1 else f"Chat {chat_id}"
    username = full_name[1:] if full_name.startswith("@") and " " not in full_name else None
    if username:
        full_name = username
    return chat_id, username, full_name
