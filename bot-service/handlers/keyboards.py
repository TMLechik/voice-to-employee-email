from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from ml_service import RecipientCandidate
from repositories import Recipient


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Добавить получателя",
                    callback_data="recipient:add",
                )
            ],
            [
                InlineKeyboardButton(text="Мои получатели", callback_data="menu:recipients"),
                InlineKeyboardButton(text="Отправить", callback_data="send:menu"),
            ],
            [
                InlineKeyboardButton(text="Удалить", callback_data="recipient:remove_menu"),
                InlineKeyboardButton(text="Показать ID", callback_data="menu:id"),
            ],
            [InlineKeyboardButton(text="Справка", callback_data="menu:help")],
        ]
    )


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="В меню", callback_data="menu:main")],
        ]
    )


def recipients_list_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Отправить", callback_data="send:menu"),
                InlineKeyboardButton(text="Удалить", callback_data="recipient:remove_menu"),
            ],
            [InlineKeyboardButton(text="В меню", callback_data="menu:main")],
        ]
    )


def empty_recipients_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Добавить получателя",
                    callback_data="recipient:add",
                )
            ],
            [InlineKeyboardButton(text="В меню", callback_data="menu:main")],
        ]
    )


def remove_targets_keyboard(recipients: list[Recipient]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=_recipient_button_text(recipient),
                callback_data=f"recipient:remove:{recipient.id}",
            )
        ]
        for recipient in recipients
    ]
    rows.append([InlineKeyboardButton(text="В меню", callback_data="menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def cancel_add_recipient_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Отмена", callback_data="recipient:add_cancel")],
        ]
    )


def voice_confirmation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Отправить",
                    callback_data="voice_match:confirm",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Отмена",
                    callback_data="voice_match:cancel",
                )
            ],
        ]
    )


def voice_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Отмена",
                    callback_data="voice_match:cancel",
                )
            ],
        ]
    )


def _recipient_button_text(recipient: Recipient) -> str:
    title = recipient.full_name or recipient.username or str(recipient.telegram_chat_id)
    return title[:60]


def recipient_candidates_keyboard(candidates: list[RecipientCandidate]) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []

    for candidate in candidates[:3]:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{candidate.recipient.full_name} ({candidate.score:.0f}%)",
                    callback_data=f"voice_match:recipient:{candidate.recipient.id}",
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="Отмена",
                callback_data="voice_match:cancel",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)
