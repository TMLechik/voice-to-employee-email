from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

from services import BotService

from .common import edit_or_answer, ensure_client, ensure_client_from_callback, recipient_title
from .keyboards import back_to_menu_keyboard, empty_recipients_keyboard, remove_targets_keyboard


def get_router(service: BotService) -> Router:
    router = Router(name="remove-recipient-command")

    @router.message(Command("remove_recipient"))
    async def remove_recipient(message: Message, command: CommandObject) -> None:
        client = ensure_client(service, message)
        selector = (command.args or "").strip()
        if not selector:
            await message.answer(
                "Укажите получателя: /remove_recipient <номер|chat_id|@username>",
                reply_markup=back_to_menu_keyboard(),
            )
            return

        linked_recipients = service.list_recipients(client.id)
        recipient = service.select_recipient(linked_recipients, selector)
        if recipient is None:
            await message.answer(
                "Такой получатель не найден в вашем списке.",
                reply_markup=back_to_menu_keyboard(),
            )
            return

        service.remove_recipient(client.id, recipient)
        await message.answer(
            f"Связь с получателем удалена: {recipient_title(recipient)}",
            reply_markup=back_to_menu_keyboard(),
        )

    @router.callback_query(F.data == "recipient:remove_menu")
    async def remove_recipient_menu(callback: CallbackQuery) -> None:
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
            "Выберите получателя, которого нужно удалить:",
            reply_markup=remove_targets_keyboard(linked_recipients),
        )

    @router.callback_query(F.data.startswith("recipient:remove:"))
    async def remove_recipient_callback(callback: CallbackQuery) -> None:
        client = ensure_client_from_callback(service, callback)
        recipient_id = _recipient_id_from_callback(callback.data)
        if recipient_id is None:
            await callback.answer("Некорректный получатель.", show_alert=True)
            return

        linked_recipients = service.list_recipients(client.id)
        recipient = service.select_recipient_by_id(linked_recipients, recipient_id)
        if recipient is None:
            await edit_or_answer(
                callback,
                "Такой получатель не найден в вашем списке.",
                reply_markup=back_to_menu_keyboard(),
            )
            return

        service.remove_recipient(client.id, recipient)
        await edit_or_answer(
            callback,
            f"Связь с получателем удалена: {recipient_title(recipient)}",
            reply_markup=back_to_menu_keyboard(),
        )

    return router


def _recipient_id_from_callback(data: str | None) -> int | None:
    if not data:
        return None

    raw_recipient_id = data.removeprefix("recipient:remove:")
    if not raw_recipient_id.isdigit():
        return None
    return int(raw_recipient_id)
