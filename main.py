# main.py

import asyncio
import logging
import os
import traceback

os.environ.setdefault("COMSPEC", r"C:\Windows\System32\cmd.exe")

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramNetworkError
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from handlers import start, catalog, books
from handlers.admin import register_admin_handlers  
from data.database import init_db
from handlers.search import register_handlers as register_search_handlers


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    #  parse_mode
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="Markdown")
    )

    dp = Dispatcher(storage=MemoryStorage())

    await init_db()

    start.register_handlers(dp)
    catalog.register_handlers(dp)
    books.register_handlers(dp)
    register_admin_handlers(dp)
    register_search_handlers(dp)

    print("Bot successfully started!")
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.warning("KeyboardInterrupt inside start_polling()")
        logger.warning("Traceback:\n%s", traceback.format_exc())
        raise
    except asyncio.CancelledError:
        logger.warning("Polling cancelled (asyncio.CancelledError)")
        logger.warning("Traceback:\n%s", traceback.format_exc())
        raise
    except TelegramNetworkError as e:
        # Noisy SSL shutdown edge-case on Ctrl+C in some Windows setups.
        if "APPLICATION_DATA_AFTER_CLOSE_NOTIFY" not in str(e):
            logger.exception("TelegramNetworkError (not ignored SSL shutdown edge-case)")
            raise
        logger.info("Polling interrupted during SSL shutdown.")
    except Exception:
        logger.exception("Unexpected exception in start_polling()")
        raise
    finally:
        logger.info("Closing bot session")
        await bot.session.close()
        logger.info("Bot session closed")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
    except Exception:
        logger.exception("Fatal error at top level")

