import asyncio
import logging
import tempfile
from pathlib import Path

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from ml_service import RecipientMatcher, RuBertSlotFillingService, SpeechToTextService
from repositories import Recipient
from services import BotService

from .common import edit_or_answer, ensure_client, ensure_client_from_callback, recipient_title
from .keyboards import (
    back_to_menu_keyboard,
    empty_recipients_keyboard,
    recipient_candidates_keyboard,
    voice_cancel_keyboard,
    voice_confirmation_keyboard,
)

logger = logging.getLogger(__name__)


def get_router(
    service: BotService,
    stt_service: SpeechToTextService,
    slot_filling_service: RuBertSlotFillingService,
    recipient_matcher: RecipientMatcher,
) -> Router:
    router = Router(name="send-command")

    @router.callback_query(F.data == "send:menu")
    async def send_menu(callback: CallbackQuery) -> None:
        client = ensure_client_from_callback(service, callback)
        if not isinstance(callback.message, Message):
            await callback.answer("Не удалось определить текущий чат.", show_alert=True)
            return

        pending_command = service.get_pending_voice_command(
            callback.from_user.id,
            callback.message.chat.id,
        )
        if pending_command is not None:
            reply_markup = (
                voice_confirmation_keyboard()
                if pending_command.selected_recipient_id is not None
                else voice_cancel_keyboard()
            )
            await edit_or_answer(
                callback,
                "Сначала подтвердите или отмените предыдущее распознанное сообщение.",
                reply_markup=reply_markup,
            )
            return

        linked_recipients = service.list_recipients(client.id)
        if not linked_recipients:
            await edit_or_answer(
                callback,
                "Получатели пока не добавлены.",
                reply_markup=empty_recipients_keyboard(),
            )
            return

        service.cancel_pending_recipient_input(callback.from_user.id)
        service.create_pending_voice_input(callback.from_user.id, callback.message.chat.id)
        await edit_or_answer(
            callback,
            "Отправьте голосовое сообщение.\n\n"
            "В голосовом назовите получателя и текст сообщения. Например:\n"
            "Передай Ивану Иванову, что встреча переносится на 15:00",
            reply_markup=voice_cancel_keyboard(),
        )

    @router.message(PendingVoiceTextFilter(service))
    async def reject_text_for_voice_send(message: Message) -> None:
        await message.answer(
            "Для отправки нужно голосовое сообщение. Запишите голосом получателя и текст.",
            reply_markup=voice_cancel_keyboard(),
        )

    @router.message(PendingVoiceInputFilter(service))
    async def process_pending_voice_message(message: Message, bot: Bot) -> None:
        await _process_voice_message(
            service=service,
            stt_service=stt_service,
            slot_filling_service=slot_filling_service,
            recipient_matcher=recipient_matcher,
            message=message,
            bot=bot,
        )

    @router.message(F.voice)
    async def reject_voice_without_send_button(message: Message) -> None:
        if message.from_user is None:
            return

        pending_command = service.get_pending_voice_command(message.from_user.id, message.chat.id)
        if pending_command is not None:
            reply_markup = (
                voice_confirmation_keyboard()
                if pending_command.selected_recipient_id is not None
                else voice_cancel_keyboard()
            )
            await message.answer(
                "Сначала подтвердите или отмените предыдущее распознанное сообщение.",
                reply_markup=reply_markup,
            )
            return

        await message.answer(
            "Чтобы отправить сообщение, нажмите кнопку «Отправить» в меню и затем пришлите голосовое.",
            reply_markup=back_to_menu_keyboard(),
        )

    @router.callback_query(F.data.startswith("voice_match:recipient:"))
    async def select_voice_candidate(callback: CallbackQuery) -> None:
        client = ensure_client_from_callback(service, callback)
        if not isinstance(callback.message, Message):
            await callback.answer("Не удалось определить текущий чат.", show_alert=True)
            return

        recipient_id = _recipient_id_from_voice_callback(callback.data)
        if recipient_id is None:
            await callback.answer("Некорректный получатель.", show_alert=True)
            return

        pending_command = service.select_pending_voice_recipient(
            telegram_user_id=callback.from_user.id,
            source_chat_id=callback.message.chat.id,
            recipient_id=recipient_id,
        )
        if pending_command is None:
            await edit_or_answer(
                callback,
                "Не нашел ожидающее голосовое сообщение. Начните заново.",
                reply_markup=back_to_menu_keyboard(),
            )
            return

        recipient = service.select_recipient_by_id(
            service.list_recipients(client.id),
            recipient_id,
        )
        if recipient is None:
            await edit_or_answer(
                callback,
                "Получатель больше не найден в вашем списке.",
                reply_markup=back_to_menu_keyboard(),
            )
            return

        await edit_or_answer(
            callback,
            _format_voice_confirmation(
                pending_command,
                recipient,
            ),
            reply_markup=voice_confirmation_keyboard(),
        )

    @router.callback_query(F.data == "voice_match:confirm")
    async def confirm_voice_send(callback: CallbackQuery, bot: Bot) -> None:
        client = ensure_client_from_callback(service, callback)
        if not isinstance(callback.message, Message):
            await callback.answer("Не удалось определить текущий чат.", show_alert=True)
            return

        pending_command = service.get_pending_voice_command(
            callback.from_user.id,
            callback.message.chat.id,
        )
        if pending_command is None or pending_command.selected_recipient_id is None:
            await edit_or_answer(
                callback,
                "Нет сообщения для подтверждения.",
                reply_markup=back_to_menu_keyboard(),
            )
            return

        recipient = service.select_recipient_by_id(
            service.list_recipients(client.id),
            pending_command.selected_recipient_id,
        )
        if recipient is None:
            service.cancel_pending_voice_command(callback.from_user.id)
            await edit_or_answer(
                callback,
                "Получатель больше не найден в вашем списке.",
                reply_markup=back_to_menu_keyboard(),
            )
            return

        service.consume_pending_voice_command(callback.from_user.id, callback.message.chat.id)
        await callback.answer()
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except TelegramAPIError:
            pass

        await _send_to_recipients(
            bot=bot,
            source_message=callback.message,
            target_chat_ids=[recipient.telegram_chat_id],
            target_titles=[recipient_title(recipient)],
            text=_outgoing_text(recipient, pending_command.message_text),
        )

    @router.callback_query(F.data == "voice_match:cancel")
    async def cancel_voice_send(callback: CallbackQuery) -> None:
        service.cancel_pending_voice_input(callback.from_user.id)
        service.cancel_pending_voice_command(callback.from_user.id)
        await edit_or_answer(
            callback,
            "Отправка голосового сообщения отменена.",
            reply_markup=back_to_menu_keyboard(),
        )

    return router


class PendingVoiceInputFilter(BaseFilter):
    def __init__(self, service: BotService) -> None:
        self.service = service

    async def __call__(self, message: Message) -> bool:
        if message.from_user is None or message.voice is None:
            return False
        return self.service.get_pending_voice_input(
            message.from_user.id,
            message.chat.id,
        ) is not None


class PendingVoiceTextFilter(BaseFilter):
    def __init__(self, service: BotService) -> None:
        self.service = service

    async def __call__(self, message: Message) -> bool:
        if message.from_user is None or message.text is None:
            return False
        return self.service.get_pending_voice_input(
            message.from_user.id,
            message.chat.id,
        ) is not None


async def _process_voice_message(
    service: BotService,
    stt_service: SpeechToTextService,
    slot_filling_service: RuBertSlotFillingService,
    recipient_matcher: RecipientMatcher,
    message: Message,
    bot: Bot,
) -> None:
    if message.from_user is None:
        return

    client = ensure_client(service, message)
    recipients = service.list_recipients(client.id)
    if not recipients:
        service.cancel_pending_voice_input(message.from_user.id)
        await message.answer(
            "Получатели пока не добавлены.",
            reply_markup=empty_recipients_keyboard(),
        )
        return

    await message.answer("Распознаю голосовое сообщение...")
    recognized_text = await _transcribe_voice_message(bot, message, stt_service)
    if not recognized_text:
        await message.answer(
            "Не удалось распознать голосовое сообщение. Отправьте другое голосовое.",
            reply_markup=voice_cancel_keyboard(),
        )
        return

    slot_result = await asyncio.to_thread(slot_filling_service.extract, recognized_text)
    if not slot_result.recipient or not slot_result.message:
        await message.answer(
            "Я распознал голос, но не смог надежно выделить получателя и текст.\n\n"
            f"Распознанный текст:\n{_clip(recognized_text)}\n\n"
            "Отправьте другое голосовое с получателем и сообщением.",
            reply_markup=voice_cancel_keyboard(),
        )
        return

    aliases_by_recipient_id = service.list_recipient_aliases(recipients)
    match_result = recipient_matcher.match(
        query=slot_result.recipient,
        recipients=recipients,
        aliases_by_recipient_id=aliases_by_recipient_id,
    )

    if match_result.is_exact or match_result.is_confident:
        recipient = match_result.recipient
        if recipient is None:
            await message.answer(
                "Получатель не найден в вашем списке.",
                reply_markup=voice_cancel_keyboard(),
            )
            return

        service.consume_pending_voice_input(message.from_user.id, message.chat.id)
        pending_command = service.create_pending_voice_command(
            telegram_user_id=message.from_user.id,
            source_chat_id=message.chat.id,
            recognized_text=recognized_text,
            recipient_query=slot_result.recipient,
            message_text=slot_result.message,
            candidate_ids=[recipient.id],
            selected_recipient_id=recipient.id,
        )
        await message.answer(
            _format_voice_confirmation(
                pending_command,
                recipient,
            ),
            reply_markup=voice_confirmation_keyboard(),
        )
        return

    candidates = match_result.candidates
    if not candidates:
        await message.answer(
            "Получатель не найден в вашем списке.\n\n"
            f"Извлеченное имя: {_clip(slot_result.recipient)}\n\n"
            "Отправьте другое голосовое или добавьте нужного получателя.",
            reply_markup=voice_cancel_keyboard(),
        )
        return

    service.consume_pending_voice_input(message.from_user.id, message.chat.id)
    service.create_pending_voice_command(
        telegram_user_id=message.from_user.id,
        source_chat_id=message.chat.id,
        recognized_text=recognized_text,
        recipient_query=slot_result.recipient,
        message_text=slot_result.message,
        candidate_ids=[candidate.recipient.id for candidate in candidates],
    )
    await message.answer(
        _format_voice_candidate_choice(
            recognized_text=recognized_text,
            recipient_query=slot_result.recipient,
            message_text=slot_result.message,
        ),
        reply_markup=recipient_candidates_keyboard(candidates),
    )


async def _transcribe_voice_message(
    bot: Bot,
    message: Message,
    stt_service: SpeechToTextService,
) -> str:
    if message.voice is None:
        return ""

    try:
        telegram_file = await bot.get_file(message.voice.file_id)
        if telegram_file.file_path is None:
            return ""

        with tempfile.TemporaryDirectory() as tmp_dir:
            audio_path = Path(tmp_dir) / "voice.ogg"
            with audio_path.open("wb") as destination:
                await bot.download_file(telegram_file.file_path, destination=destination)

            return await asyncio.to_thread(stt_service.transcribe, audio_path)
    except Exception:
        logger.exception("Voice message transcription failed")
        return ""


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


def _recipient_id_from_voice_callback(data: str | None) -> int | None:
    if not data:
        return None

    raw_recipient_id = data.removeprefix("voice_match:recipient:")
    if not raw_recipient_id.isdigit():
        return None
    return int(raw_recipient_id)


def _format_voice_confirmation(
    pending_command,
    recipient: Recipient,
) -> str:
    return (
        "Проверьте перед отправкой.\n\n"
        f"Распознанное голосовое:\n{_clip(pending_command.recognized_text)}\n\n"
        f"Получатель из голосового: {_clip(pending_command.recipient_query)}\n"
        f"Получатель в БД: {recipient_title(recipient)}\n\n"
        f"Сообщение будет отправлено так:\n"
        f"{_clip(_outgoing_text(recipient, pending_command.message_text))}"
    )


def _format_voice_candidate_choice(
    recognized_text: str,
    recipient_query: str,
    message_text: str,
) -> str:
    return (
        "Я не уверен, кому отправить сообщение. Выберите получателя.\n\n"
        f"Распознанное голосовое:\n{_clip(recognized_text)}\n\n"
        f"Получатель из голосового: {_clip(recipient_query)}\n\n"
        f"Текст сообщения:\n{_clip(message_text)}"
    )


def _outgoing_text(recipient: Recipient, message_text: str) -> str:
    return f"{recipient_title(recipient)}, {message_text}"


def _clip(value: str, limit: int = 700) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."
