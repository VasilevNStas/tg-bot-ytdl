# SPDX-FileCopyrightText: Copyright (c) 2026 VasilevNStas
# SPDX-License-Identifier: MIT
"""Command handlers for the bot."""

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

router = Router(name="common")

START_TEXT = (
    "Привет! Отправь мне ссылку на видео YouTube, "
    "и я покажу доступные форматы для скачивания."
)

HELP_TEXT = (
    "Как пользоваться:\n"
    "1. Отправь ссылку на видео YouTube.\n"
    "2. Выбери нужный формат из списка.\n"
    "3. Получи готовый файл.\n\n"
    "Команды:\n"
    "/start — начать\n"
    "/help — эта справка"
)


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    """Reply to the /start command."""
    await message.answer(START_TEXT)


@router.message(Command("help"))
async def handle_help(message: Message) -> None:
    """Reply to the /help command."""
    await message.answer(HELP_TEXT)
