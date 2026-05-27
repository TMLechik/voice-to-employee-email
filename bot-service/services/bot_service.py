from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from repositories import Client, Recipient, SQLiteBotRepository


@dataclass(frozen=True)
class PendingRecipientInput:
    source_chat_id: int


@dataclass(frozen=True)
class PendingVoiceInput:
    source_chat_id: int


@dataclass(frozen=True)
class PendingVoiceCommand:
    source_chat_id: int
    recognized_text: str
    recipient_query: str
    message_text: str
    candidate_ids: list[int]
    selected_recipient_id: int | None = None


class BotService:
    def __init__(self, repository: SQLiteBotRepository) -> None:
        self.repository = repository
        self._pending_recipient_inputs: dict[int, PendingRecipientInput] = {}
        self._pending_voice_inputs: dict[int, PendingVoiceInput] = {}
        self._pending_voice_commands: dict[int, PendingVoiceCommand] = {}

    def register_client(
        self,
        telegram_user_id: int,
        username: str | None,
        full_name: str,
    ) -> Client:
        return self.repository.upsert_client(telegram_user_id, username, full_name)

    def add_recipient(
        self,
        client_id: int,
        telegram_chat_id: int,
        username: str | None,
        full_name: str,
    ) -> Recipient:
        recipient = self.repository.upsert_recipient(telegram_chat_id, username, full_name)
        self.repository.link_client_recipient(client_id, recipient.id)
        return recipient

    def list_recipients(self, client_id: int) -> list[Recipient]:
        return self.repository.list_recipients(client_id)

    def list_recipient_aliases(self, recipients: list[Recipient]) -> dict[int, list[str]]:
        return self.repository.list_recipient_aliases(
            [recipient.id for recipient in recipients]
        )

    def remove_recipient(self, client_id: int, recipient: Recipient) -> bool:
        was_removed = self.repository.unlink_recipient(client_id, recipient.id)
        if was_removed:
            self.repository.remove_orphan_recipients()
        return was_removed

    def select_recipient(
        self,
        recipients: Iterable[Recipient],
        selector: str,
    ) -> Recipient | None:
        recipients_list = list(recipients)
        normalized = selector.strip()
        if not normalized:
            return None

        if _is_int(normalized):
            value = int(normalized)
            for recipient in recipients_list:
                if recipient.telegram_chat_id == value:
                    return recipient

            if value > 0 and value <= len(recipients_list):
                return recipients_list[value - 1]

        normalized_username = normalized.lstrip("@").lower()
        for recipient in recipients_list:
            if recipient.username and recipient.username.lower() == normalized_username:
                return recipient

        return None

    def select_recipient_by_id(
        self,
        recipients: Iterable[Recipient],
        recipient_id: int,
    ) -> Recipient | None:
        for recipient in recipients:
            if recipient.id == recipient_id:
                return recipient
        return None

    def create_pending_recipient_input(
        self,
        telegram_user_id: int,
        source_chat_id: int,
    ) -> PendingRecipientInput:
        pending_input = PendingRecipientInput(source_chat_id=source_chat_id)
        self._pending_recipient_inputs[telegram_user_id] = pending_input
        return pending_input

    def get_pending_recipient_input(
        self,
        telegram_user_id: int,
        source_chat_id: int,
    ) -> PendingRecipientInput | None:
        pending_input = self._pending_recipient_inputs.get(telegram_user_id)
        if pending_input is None or pending_input.source_chat_id != source_chat_id:
            return None
        return pending_input

    def consume_pending_recipient_input(
        self,
        telegram_user_id: int,
        source_chat_id: int,
    ) -> PendingRecipientInput | None:
        pending_input = self.get_pending_recipient_input(telegram_user_id, source_chat_id)
        if pending_input is not None:
            self._pending_recipient_inputs.pop(telegram_user_id, None)
        return pending_input

    def cancel_pending_recipient_input(self, telegram_user_id: int) -> bool:
        return self._pending_recipient_inputs.pop(telegram_user_id, None) is not None

    def create_pending_voice_input(
        self,
        telegram_user_id: int,
        source_chat_id: int,
    ) -> PendingVoiceInput:
        pending_input = PendingVoiceInput(source_chat_id=source_chat_id)
        self._pending_voice_inputs[telegram_user_id] = pending_input
        return pending_input

    def get_pending_voice_input(
        self,
        telegram_user_id: int,
        source_chat_id: int,
    ) -> PendingVoiceInput | None:
        pending_input = self._pending_voice_inputs.get(telegram_user_id)
        if pending_input is None or pending_input.source_chat_id != source_chat_id:
            return None
        return pending_input

    def consume_pending_voice_input(
        self,
        telegram_user_id: int,
        source_chat_id: int,
    ) -> PendingVoiceInput | None:
        pending_input = self.get_pending_voice_input(telegram_user_id, source_chat_id)
        if pending_input is not None:
            self._pending_voice_inputs.pop(telegram_user_id, None)
        return pending_input

    def cancel_pending_voice_input(self, telegram_user_id: int) -> bool:
        return self._pending_voice_inputs.pop(telegram_user_id, None) is not None

    def create_pending_voice_command(
        self,
        telegram_user_id: int,
        source_chat_id: int,
        recognized_text: str,
        recipient_query: str,
        message_text: str,
        candidate_ids: list[int],
        selected_recipient_id: int | None = None,
    ) -> PendingVoiceCommand:
        pending_command = PendingVoiceCommand(
            source_chat_id=source_chat_id,
            recognized_text=recognized_text,
            recipient_query=recipient_query,
            message_text=message_text,
            candidate_ids=candidate_ids,
            selected_recipient_id=selected_recipient_id,
        )
        self._pending_voice_commands[telegram_user_id] = pending_command
        return pending_command

    def get_pending_voice_command(
        self,
        telegram_user_id: int,
        source_chat_id: int,
    ) -> PendingVoiceCommand | None:
        pending_command = self._pending_voice_commands.get(telegram_user_id)
        if pending_command is None or pending_command.source_chat_id != source_chat_id:
            return None
        return pending_command

    def select_pending_voice_recipient(
        self,
        telegram_user_id: int,
        source_chat_id: int,
        recipient_id: int,
    ) -> PendingVoiceCommand | None:
        pending_command = self.get_pending_voice_command(telegram_user_id, source_chat_id)
        if pending_command is None or recipient_id not in pending_command.candidate_ids:
            return None

        return self.create_pending_voice_command(
            telegram_user_id=telegram_user_id,
            source_chat_id=source_chat_id,
            recognized_text=pending_command.recognized_text,
            recipient_query=pending_command.recipient_query,
            message_text=pending_command.message_text,
            candidate_ids=pending_command.candidate_ids,
            selected_recipient_id=recipient_id,
        )

    def consume_pending_voice_command(
        self,
        telegram_user_id: int,
        source_chat_id: int,
    ) -> PendingVoiceCommand | None:
        pending_command = self.get_pending_voice_command(telegram_user_id, source_chat_id)
        if pending_command is not None:
            self._pending_voice_commands.pop(telegram_user_id, None)
        return pending_command

    def cancel_pending_voice_command(self, telegram_user_id: int) -> bool:
        return self._pending_voice_commands.pop(telegram_user_id, None) is not None


def _is_int(value: str) -> bool:
    return value.lstrip("-").isdigit()
