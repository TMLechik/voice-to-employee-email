import asyncio
import logging
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ML_SERVICE_DIR = PROJECT_ROOT / "ml-service"
if str(ML_SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(ML_SERVICE_DIR))

from config import Settings
from handlers import create_router
from ml_service import RecipientMatcher, RuBertSlotFillingService, SpeechToTextService
from repositories import SQLiteBotRepository
from services import BotService


async def run() -> None:
    settings = Settings.from_env()

    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    repository = SQLiteBotRepository(settings.db_path, settings.schema_path)
    repository.initialize()
    service = BotService(repository)
    stt_service = SpeechToTextService(
        model_size=settings.stt_model_size,
        device=settings.stt_device,
    )
    slot_filling_service = RuBertSlotFillingService(settings.slot_filling_model_path)
    recipient_matcher = RecipientMatcher()

    bot = Bot(token=settings.bot_token)
    dispatcher = Dispatcher()
    dispatcher.include_router(
        create_router(
            service=service,
            stt_service=stt_service,
            slot_filling_service=slot_filling_service,
            recipient_matcher=recipient_matcher,
        )
    )

    logging.getLogger(__name__).info("Bot service started with database %s", settings.db_path)
    await dispatcher.start_polling(bot)


def main() -> None:
    try:
        asyncio.run(run())
    except (KeyboardInterrupt, SystemExit):
        logging.getLogger(__name__).info("Bot service stopped")


if __name__ == "__main__":
    main()
