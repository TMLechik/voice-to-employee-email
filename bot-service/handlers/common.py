from __future__ import annotations

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message, User

from repositories import Client, Recipient
from services import BotService


MENU_TEXT = """Главное меню

Выберите действие кнопкой ниже."""

HELP_TEXT = """Основные действия доступны кнопками в меню.

Можно также использовать команды:
/start - открыть главное меню
/id - показать Telegram ID текущего пользователя и чата
/add_recipient - добавить текущий чат как получателя
/add_recipient <chat_id> <название> - добавить получателя по chat_id
/recipients - показать связанных получателей
/remove_recipient <номер|chat_id|@username> - удалить связь с получателем
/send <номер|chat_id|@username|all> <текст> - отправить сообщение"""


def ensure_client(service: BotService, message: Message) -> Client:
    if message.from_user is None:
        raise RuntimeError("Telegram update has no user data.")

    return service.register_client(
        telegram_user_id=message.from_user.id,
        username=message.from_user.username,
        full_name=user_full_name(message),
    )


def ensure_client_from_callback(service: BotService, callback: CallbackQuery) -> Client:
    return service.register_client(
        telegram_user_id=callback.from_user.id,
        username=callback.from_user.username,
        full_name=user_full_name_from_user(callback.from_user),
    )


def user_full_name(message: Message) -> str:
    if message.from_user is None:
        return "Unknown user"

    return user_full_name_from_user(message.from_user)


def user_full_name_from_user(user: User) -> str:
    full_name = " ".join(
        part
        for part in (user.first_name, user.last_name)
        if part
    ).strip()
    return full_name or user.username or str(user.id)


def chat_username(message: Message) -> str | None:
    username = getattr(message.chat, "username", None)
    return username or None


def chat_full_name(message: Message) -> str:
    title = getattr(message.chat, "title", None)
    if title:
        return title

    if message.chat.type == "private":
        return user_full_name(message)

    return f"Chat {message.chat.id}"


def recipient_title(recipient: Recipient) -> str:
    return recipient.full_name or recipient.username or str(recipient.telegram_chat_id)


def format_recipients(recipients: list[Recipient]) -> str:
    if not recipients:
        return "Получатели пока не добавлены."

    lines = ["Ваши получатели:"]
    for index, recipient in enumerate(recipients, start=1):
        username = f" @{recipient.username}" if recipient.username else ""
        lines.append(
            f"{index}. {recipient_title(recipient)}{username} "
            f"(chat_id: {recipient.telegram_chat_id})"
        )
    return "\n".join(lines)


async def edit_or_answer(
    callback: CallbackQuery,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    if isinstance(callback.message, Message):
        try:
            await callback.message.edit_text(text, reply_markup=reply_markup)
        except TelegramBadRequest as error:
            if "message is not modified" not in str(error).lower():
                await callback.message.answer(text, reply_markup=reply_markup)
        await callback.answer()
    else:
        await callback.answer(text, show_alert=True)
