from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .models import Client, Recipient


class SQLiteBotRepository:
    def __init__(self, db_path: Path, schema_path: Path) -> None:
        self.db_path = db_path
        self.schema_path = schema_path

    def initialize(self) -> None:
        if not self.schema_path.exists():
            raise FileNotFoundError(f"Database schema was not found: {self.schema_path}")

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(self.schema_path.read_text(encoding="utf-8"))

    def upsert_client(
        self,
        telegram_user_id: int,
        username: str | None,
        full_name: str,
    ) -> Client:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO telegram_bot_clients (telegram_user_id, username, full_name)
                VALUES (?, ?, ?)
                ON CONFLICT(telegram_user_id) DO UPDATE SET
                    username = excluded.username,
                    full_name = excluded.full_name
                """,
                (telegram_user_id, username, full_name),
            )
            row = connection.execute(
                """
                SELECT id, telegram_user_id, username, full_name
                FROM telegram_bot_clients
                WHERE telegram_user_id = ?
                """,
                (telegram_user_id,),
            ).fetchone()
            return _client_from_row(row)

    def upsert_recipient(
        self,
        telegram_chat_id: int,
        username: str | None,
        full_name: str,
    ) -> Recipient:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO message_recipients (telegram_chat_id, username, full_name)
                VALUES (?, ?, ?)
                ON CONFLICT(telegram_chat_id) DO UPDATE SET
                    username = excluded.username,
                    full_name = excluded.full_name
                """,
                (telegram_chat_id, username, full_name),
            )
            row = connection.execute(
                """
                SELECT id, telegram_chat_id, username, full_name
                FROM message_recipients
                WHERE telegram_chat_id = ?
                """,
                (telegram_chat_id,),
            ).fetchone()
            return _recipient_from_row(row)

    def link_client_recipient(self, client_id: int, recipient_id: int) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO client_recipient_links (client_id, recipient_id)
                VALUES (?, ?)
                """,
                (client_id, recipient_id),
            )

    def list_recipients(self, client_id: int) -> list[Recipient]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT r.id, r.telegram_chat_id, r.username, r.full_name
                FROM message_recipients AS r
                INNER JOIN client_recipient_links AS l ON l.recipient_id = r.id
                WHERE l.client_id = ?
                ORDER BY r.full_name COLLATE NOCASE, r.telegram_chat_id
                """,
                (client_id,),
            ).fetchall()
            return [_recipient_from_row(row) for row in rows]

    def unlink_recipient(self, client_id: int, recipient_id: int) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                DELETE FROM client_recipient_links
                WHERE client_id = ? AND recipient_id = ?
                """,
                (client_id, recipient_id),
            )
            return cursor.rowcount > 0

    def remove_orphan_recipients(self) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                DELETE FROM message_recipients
                WHERE id NOT IN (
                    SELECT DISTINCT recipient_id
                    FROM client_recipient_links
                )
                """
            )
            return cursor.rowcount

    def add_recipient_alias(self, recipient_id: int, alias: str) -> None:
        normalized_alias = alias.strip()
        if not normalized_alias:
            return

        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO recipient_aliases (recipient_id, alias)
                VALUES (?, ?)
                """,
                (recipient_id, normalized_alias),
            )

    def list_recipient_aliases(self, recipient_ids: list[int]) -> dict[int, list[str]]:
        if not recipient_ids:
            return {}

        placeholders = ",".join("?" for _ in recipient_ids)

        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT recipient_id, alias
                FROM recipient_aliases
                WHERE recipient_id IN ({placeholders})
                ORDER BY alias COLLATE NOCASE
                """,
                recipient_ids,
            ).fetchall()

        aliases_by_recipient_id: dict[int, list[str]] = {
            recipient_id: [] for recipient_id in recipient_ids
        }

        for row in rows:
            aliases_by_recipient_id[int(row["recipient_id"])].append(row["alias"])

        return aliases_by_recipient_id

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()


def _client_from_row(row: sqlite3.Row | None) -> Client:
    if row is None:
        raise LookupError("Client row was not found after database write.")

    return Client(
        id=int(row["id"]),
        telegram_user_id=int(row["telegram_user_id"]),
        username=row["username"],
        full_name=row["full_name"],
    )


def _recipient_from_row(row: sqlite3.Row | None) -> Recipient:
    if row is None:
        raise LookupError("Recipient row was not found after database write.")

    return Recipient(
        id=int(row["id"]),
        telegram_chat_id=int(row["telegram_chat_id"]),
        username=row["username"],
        full_name=row["full_name"],
    )
