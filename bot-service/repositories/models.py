from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Client:
    id: int
    telegram_user_id: int
    username: str | None
    full_name: str


@dataclass(frozen=True)
class Recipient:
    id: int
    telegram_chat_id: int
    username: str | None
    full_name: str
