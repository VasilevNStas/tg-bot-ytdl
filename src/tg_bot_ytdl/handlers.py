# SPDX-FileCopyrightText: Copyright (c) 2026 VasilevNStas
# SPDX-License-Identifier: MIT
"""Command handlers for the bot."""

import logging
import tempfile

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, ErrorEvent, FSInputFile, Message
from aiogram.types import User as TelegramUser

from tg_bot_ytdl.db import session_scope
from tg_bot_ytdl.downloader import (
    MAX_FILE_SIZE,
    DownloadError,
    fetch_format,
)
from tg_bot_ytdl.extractor import (
    ExtractionError,
    VideoFormat,
    VideoInfo,
    fetch_video_info,
    is_supported_url,
)
from tg_bot_ytdl.keyboards import CALLBACK_PREFIX, build_formats_keyboard
from tg_bot_ytdl.ratelimit import RateLimiter
from tg_bot_ytdl.repository import (
    STATUS_FAILED,
    STATUS_SENT,
    STATUS_TOO_LARGE,
    get_or_create_user,
    record_download,
)

router = Router(name="common")

_last_video: dict[int, VideoInfo] = {}

_rate_limiter = RateLimiter()

logger = logging.getLogger(__name__)

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
    _touch_user(message.from_user)
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

FORMAT_SELECTED_TEXT = "Формат выбран."

DOWNLOADING_TEXT = "Скачиваю файл..."

TOO_LARGE_TEXT = (
    "Файл слишком большой для отправки через Telegram "
    "(лимит 50 МБ). Выбери формат меньшего размера."
)

DOWNLOAD_FAILED_TEXT = "Не удалось скачать файл. Попробуй другой формат."

SELECTION_EXPIRED_TEXT = "Не удалось найти выбранный формат. Отправь ссылку заново."

RATE_LIMITED_TEXT = "Слишком часто. Подожди пару секунд и попробуй снова."

UNEXPECTED_ERROR_TEXT = "Что-то пошло не так. Попробуй ещё раз позже."


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


def _touch_user(user: TelegramUser | None) -> None:
    """Register or refresh the given Telegram user."""
    if user is None:
        return
    with session_scope() as session:
        get_or_create_user(session, user.id, user.username)


def _record_download(
    user: TelegramUser | None,
    info: VideoInfo,
    fmt: VideoFormat,
    status: str,
) -> None:
    """Persist a download attempt made by the given user."""
    if user is None:
        return
    with session_scope() as session:
        record_download(
            session,
            user.id,
            user.username,
            info=info,
            fmt=fmt,
            status=status,
        )


@router.message(F.text)
async def handle_link(message: Message) -> None:
    """Validate a YouTube link and reply with its metadata."""
    text = (message.text or "").strip()
    if text.startswith("/"):
        return
    user = message.from_user
    if user is not None and not _rate_limiter.allow(user.id):
        await message.answer(RATE_LIMITED_TEXT)
        return
    _touch_user(user)
    if not is_supported_url(text):
        await message.answer(NOT_A_LINK_TEXT)
        return

    await message.answer(PROCESSING_TEXT)
    try:
        info = await fetch_video_info(text)
    except ExtractionError:
        await message.answer(EXTRACTION_FAILED_TEXT)
        return
    _last_video[message.chat.id] = info
    await message.answer(
        format_info_message(info),
        reply_markup=build_formats_keyboard(info.formats),
    )


@router.callback_query(F.data.startswith(CALLBACK_PREFIX))
async def handle_format_selected(callback: CallbackQuery) -> None:
    """Download the selected format and send it as a document."""
    await callback.answer(FORMAT_SELECTED_TEXT)
    message = callback.message
    if message is None:
        return

    info = _last_video.get(message.chat.id)
    format_id = (callback.data or "")[len(CALLBACK_PREFIX) :]
    fmt = None
    if info is not None:
        fmt = next((f for f in info.formats if f.format_id == format_id), None)
    if info is None or fmt is None:
        await message.answer(SELECTION_EXPIRED_TEXT)
        return

    user = callback.from_user
    if fmt.filesize and fmt.filesize > MAX_FILE_SIZE:
        _record_download(user, info, fmt, STATUS_TOO_LARGE)
        await message.answer(TOO_LARGE_TEXT)
        return

    await message.answer(DOWNLOADING_TEXT)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            path = await fetch_format(info.url, format_id, tmp)
            if path.stat().st_size > MAX_FILE_SIZE:
                _record_download(user, info, fmt, STATUS_TOO_LARGE)
                await message.answer(TOO_LARGE_TEXT)
                return
            await message.answer_document(FSInputFile(path))
    except DownloadError:
        _record_download(user, info, fmt, STATUS_FAILED)
        await message.answer(DOWNLOAD_FAILED_TEXT)
        return
    _record_download(user, info, fmt, STATUS_SENT)


@router.errors()
async def handle_error(event: ErrorEvent) -> bool:
    """Log unexpected errors and notify the user when possible."""
    logger.exception("Unhandled error", exc_info=event.exception)
    update = event.update
    message = update.message or (
        update.callback_query.message if update.callback_query else None
    )
    if message is not None:
        try:
            await message.answer(UNEXPECTED_ERROR_TEXT)
        except Exception:
            logger.exception("Failed to notify user about the error")
    return True
