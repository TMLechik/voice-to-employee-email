from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from repositories import Client, Recipient, SQLiteBotRepository


@dataclass(frozen=True)
class PendingSend:
    source_chat_id: int
    target_chat_ids: list[int]
    target_titles: list[str]


class BotService:
    def __init__(self, repository: SQLiteBotRepository) -> None:
        self.repository = repository
        self._pending_sends: dict[int, PendingSend] = {}

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

    def select_recipients_for_send(
        self,
        recipients: list[Recipient],
        selector: str,
    ) -> list[Recipient]:
        if selector.lower() in {"all", "*"}:
            return recipients

        recipient = self.select_recipient(recipients, selector)
        return [recipient] if recipient else []

    def create_pending_send(
        self,
        telegram_user_id: int,
        source_chat_id: int,
        recipients: list[Recipient],
    ) -> PendingSend:
        pending_send = PendingSend(
            source_chat_id=source_chat_id,
            target_chat_ids=[recipient.telegram_chat_id for recipient in recipients],
            target_titles=[recipient.full_name for recipient in recipients],
        )
        self._pending_sends[telegram_user_id] = pending_send
        return pending_send

    def get_pending_send(
        self,
        telegram_user_id: int,
        source_chat_id: int,
    ) -> PendingSend | None:
        pending_send = self._pending_sends.get(telegram_user_id)
        if pending_send is None or pending_send.source_chat_id != source_chat_id:
            return None
        return pending_send

    def consume_pending_send(
        self,
        telegram_user_id: int,
        source_chat_id: int,
    ) -> PendingSend | None:
        pending_send = self.get_pending_send(telegram_user_id, source_chat_id)
        if pending_send is not None:
            self._pending_sends.pop(telegram_user_id, None)
        return pending_send

    def cancel_pending_send(self, telegram_user_id: int) -> bool:
        return self._pending_sends.pop(telegram_user_id, None) is not None


def _is_int(value: str) -> bool:
    return value.lstrip("-").isdigit()
