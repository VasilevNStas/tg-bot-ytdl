# SPDX-FileCopyrightText: Copyright (c) 2026 VasilevNStas
# SPDX-License-Identifier: MIT
"""Command handlers for the bot."""

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from tg_bot_ytdl.extractor import (
    ExtractionError,
    VideoInfo,
    fetch_video_info,
    is_supported_url,
)

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


NOT_A_LINK_TEXT = (
    "Это не похоже на ссылку YouTube.\n"
    "Отправь ссылку вида https://youtube.com/watch?v=... или https://youtu.be/..."
)

PROCESSING_TEXT = "Получаю информацию о видео..."

EXTRACTION_FAILED_TEXT = (
    "Не удалось получить информацию по ссылке. Проверь ссылку и попробуй снова."
)


def format_duration(seconds: int | None) -> str:
    """Format a duration in seconds as ``mm:ss`` / ``h:mm:ss``."""
    if not seconds:
        return "—"
    minutes, sec = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{sec:02d}"
    return f"{minutes}:{sec:02d}"


def format_info_message(info: VideoInfo) -> str:
    """Build the reply text describing extracted video metadata."""
    return (
        f"{info.title}\n"
        f"Автор: {info.uploader or '—'}\n"
        f"Длительность: {format_duration(info.duration)}\n"
        f"Доступно форматов: {len(info.formats)}"
    )


@router.message(F.text)
async def handle_link(message: Message) -> None:
    """Validate a YouTube link and reply with its metadata."""
    text = (message.text or "").strip()
    if text.startswith("/"):
        return
    if not is_supported_url(text):
        await message.answer(NOT_A_LINK_TEXT)
        return

    await message.answer(PROCESSING_TEXT)
    try:
        info = await fetch_video_info(text)
    except ExtractionError:
        await message.answer(EXTRACTION_FAILED_TEXT)
        return
    await message.answer(format_info_message(info))
