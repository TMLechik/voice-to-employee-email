from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import BaseFilter, Command, CommandObject
from aiogram.types import CallbackQuery, Message

from services import BotService

from .common import edit_or_answer, ensure_client, ensure_client_from_callback, recipient_title
from .keyboards import back_to_menu_keyboard, cancel_send_keyboard, empty_recipients_keyboard, send_targets_keyboard


def get_router(service: BotService) -> Router:
    router = Router(name="send-command")

    @router.message(Command("send"))
    async def send_message(message: Message, command: CommandObject, bot: Bot) -> None:
        client = ensure_client(service, message)
        args = (command.args or "").strip()
        if not args or len(args.split(maxsplit=1)) < 2:
            await message.answer(
                "Используйте: /send <номер|chat_id|@username|all> <текст>",
                reply_markup=back_to_menu_keyboard(),
            )
            return

        selector, text = args.split(maxsplit=1)
        linked_recipients = service.list_recipients(client.id)
        if not linked_recipients:
            await message.answer(
                "Сначала добавьте получателя.",
                reply_markup=empty_recipients_keyboard(),
            )
            return

        selected_recipients = service.select_recipients_for_send(linked_recipients, selector)
        if not selected_recipients:
            await message.answer(
                "Такой получатель не найден в вашем списке.",
                reply_markup=back_to_menu_keyboard(),
            )
            return

        await _send_to_recipients(
            bot=bot,
            source_message=message,
            target_chat_ids=[recipient.telegram_chat_id for recipient in selected_recipients],
            target_titles=[recipient_title(recipient) for recipient in selected_recipients],
            text=text,
        )

    @router.callback_query(F.data == "send:menu")
    async def send_menu(callback: CallbackQuery) -> None:
        client = ensure_client_from_callback(service, callback)
        linked_recipients = service.list_recipients(client.id)
        if not linked_recipients:
            await edit_or_answer(
                callback,
                "Получатели пока не добавлены.",
                reply_markup=empty_recipients_keyboard(),
            )
            return

        await edit_or_answer(
            callback,
            "Кому отправить сообщение?",
            reply_markup=send_targets_keyboard(linked_recipients),
        )

    @router.callback_query(F.data == "send:all")
    async def wait_text_for_all(callback: CallbackQuery) -> None:
        await _create_pending_send_from_callback(service, callback, recipient_id=None)

    @router.callback_query(F.data.startswith("send:recipient:"))
    async def wait_text_for_recipient(callback: CallbackQuery) -> None:
        recipient_id = _recipient_id_from_callback(callback.data)
        if recipient_id is None:
            await callback.answer("Некорректный получатель.", show_alert=True)
            return
        await _create_pending_send_from_callback(service, callback, recipient_id=recipient_id)

    @router.callback_query(F.data == "send:cancel")
    async def cancel_send(callback: CallbackQuery) -> None:
        service.cancel_pending_send(callback.from_user.id)
        await edit_or_answer(
            callback,
            "Отправка отменена.",
            reply_markup=back_to_menu_keyboard(),
        )

    @router.message(PendingSendFilter(service))
    async def send_pending_text(message: Message, bot: Bot) -> None:
        if message.from_user is None or message.text is None:
            return

        pending_send = service.consume_pending_send(message.from_user.id, message.chat.id)
        if pending_send is None:
            return

        await _send_to_recipients(
            bot=bot,
            source_message=message,
            target_chat_ids=pending_send.target_chat_ids,
            target_titles=pending_send.target_titles,
            text=message.text,
        )

    return router


class PendingSendFilter(BaseFilter):
    def __init__(self, service: BotService) -> None:
        self.service = service

    async def __call__(self, message: Message) -> bool:
        if message.from_user is None or message.text is None:
            return False
        if message.text.startswith("/"):
            return False
        return self.service.get_pending_send(message.from_user.id, message.chat.id) is not None


async def _create_pending_send_from_callback(
    service: BotService,
    callback: CallbackQuery,
    recipient_id: int | None,
) -> None:
    client = ensure_client_from_callback(service, callback)
    if not isinstance(callback.message, Message):
        await callback.answer("Не удалось определить текущий чат.", show_alert=True)
        return

    linked_recipients = service.list_recipients(client.id)
    if recipient_id is None:
        selected_recipients = linked_recipients
    else:
        recipient = service.select_recipient_by_id(linked_recipients, recipient_id)
        selected_recipients = [recipient] if recipient else []

    if not selected_recipients:
        await edit_or_answer(
            callback,
            "Такой получатель не найден в вашем списке.",
            reply_markup=back_to_menu_keyboard(),
        )
        return

    pending_send = service.create_pending_send(
        telegram_user_id=callback.from_user.id,
        source_chat_id=callback.message.chat.id,
        recipients=selected_recipients,
    )
    targets = ", ".join(pending_send.target_titles)
    await edit_or_answer(
        callback,
        "Введите текст сообщения следующим сообщением.\n"
        f"Получатели: {targets}",
        reply_markup=cancel_send_keyboard(),
    )


async def _send_to_recipients(
    bot: Bot,
    source_message: Message,
    target_chat_ids: list[int],
    target_titles: list[str],
    text: str,
) -> None:
    sent_count = 0
    failed_titles: list[str] = []
    for chat_id, title in zip(target_chat_ids, target_titles, strict=False):
        try:
            await bot.send_message(chat_id, text)
            sent_count += 1
        except TelegramAPIError:
            failed_titles.append(title)

    if failed_titles:
        await source_message.answer(
            f"Отправлено: {sent_count}. Не удалось отправить: {', '.join(failed_titles)}",
            reply_markup=back_to_menu_keyboard(),
        )
    else:
        await source_message.answer(
            f"Сообщение отправлено. Получателей: {sent_count}.",
            reply_markup=back_to_menu_keyboard(),
        )


def _recipient_id_from_callback(data: str | None) -> int | None:
    if not data:
        return None

    raw_recipient_id = data.removeprefix("send:recipient:")
    if not raw_recipient_id.isdigit():
        return None
    return int(raw_recipient_id)
