# SPDX-FileCopyrightText: Copyright (c) 2026 VasilevNStas
# SPDX-License-Identifier: MIT
"""Bot wiring and process entry point."""

import asyncio
import logging

from aiogram import Bot, Dispatcher

from tg_bot_ytdl.config import get_settings
from tg_bot_ytdl.db import init_db
from tg_bot_ytdl.handlers import router

logger = logging.getLogger(__name__)


async def main() -> None:
    """Create the bot and dispatcher and start long-polling."""
    settings = get_settings()
    init_db()
    bot = Bot(token=settings.require_bot_token())
    dp = Dispatcher()
    dp.include_router(router)

    logger.info("Starting polling...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


def run() -> None:
    """Run the bot (sync wrapper around the async ``main``)."""
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
