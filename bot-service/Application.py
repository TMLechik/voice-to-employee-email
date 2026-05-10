import asyncio
import logging

from aiogram import Bot, Dispatcher

from config import Settings
from handlers import create_router
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

    bot = Bot(token=settings.bot_token)
    dispatcher = Dispatcher()
    dispatcher.include_router(create_router(service))

    logging.getLogger(__name__).info("Bot service started with database %s", settings.db_path)
    await dispatcher.start_polling(bot)


def main() -> None:
    try:
        asyncio.run(run())
    except (KeyboardInterrupt, SystemExit):
        logging.getLogger(__name__).info("Bot service stopped")


if __name__ == "__main__":
    main()
