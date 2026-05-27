from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _path_from_env(name: str, default: Path) -> Path:
    raw_value = os.getenv(name)
    path = Path(raw_value) if raw_value else default
    return path if path.is_absolute() else BASE_DIR / path


def _log_level_from_env() -> int:
    raw_level = os.getenv("BOT_LOG_LEVEL", "INFO").upper()
    return getattr(logging, raw_level, logging.INFO)


@dataclass(frozen=True)
class Settings:
    bot_token: str
    db_path: Path
    schema_path: Path
    slot_filling_model_path: Path
    stt_model_size: str = "base"
    stt_device: str = "cpu"
    log_level: int = logging.INFO

    @classmethod
    def from_env(cls) -> "Settings":
        _load_dotenv(BASE_DIR / ".env")

        bot_token = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
        if not bot_token:
            raise RuntimeError(
                "Set BOT_TOKEN or TELEGRAM_BOT_TOKEN before starting the bot service."
            )

        return cls(
            bot_token=bot_token,
            db_path=_path_from_env("BOT_DB_PATH", BASE_DIR / "database" / "bot.sqlite3"),
            schema_path=_path_from_env("BOT_SCHEMA_PATH", BASE_DIR / "database" / "schema.sql"),
            slot_filling_model_path=_path_from_env(
                "SLOT_FILLING_MODEL_PATH",
                PROJECT_ROOT / "ml-service" / "models" / "rubert-slot-filling",
            ),
            stt_model_size=os.getenv("STT_MODEL_SIZE", "base"),
            stt_device=os.getenv("STT_DEVICE", "cpu"),
            log_level=_log_level_from_env(),
        )
