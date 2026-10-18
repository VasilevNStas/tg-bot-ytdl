# SPDX-FileCopyrightText: Copyright (c) 2026 VasilevNStas
# SPDX-License-Identifier: MIT
"""Command handlers for the bot."""

import logging
import re
import tempfile
from dataclasses import replace

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, ErrorEvent, FSInputFile, Message
from aiogram.types import User as TelegramUser

from tg_bot_ytdl.channels import (
    ChannelInfo,
    fetch_channel_info,
    is_channel_url,
)
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
from tg_bot_ytdl.keyboards import (
    CALLBACK_PREFIX,
    MENU_DOWNLOAD,
    MENU_HELP,
    MENU_SUBSCRIPTIONS,
    SUBSCRIPTION_CALLBACK_PREFIX,
    SUBSCRIPTION_DELETE_PREFIX,
    build_formats_keyboard,
    build_main_menu_keyboard,
    build_subscription_actions_keyboard,
    build_subscriptions_keyboard,
    select_formats,
)
from tg_bot_ytdl.ratelimit import RateLimiter
from tg_bot_ytdl.repository import (
    STATUS_FAILED,
    STATUS_SENT,
    STATUS_TOO_LARGE,
    add_subscription,
    get_or_create_user,
    get_subscription,
    list_subscriptions,
    record_download,
    remove_subscription,
)

router = Router(name="common")

_last_video: dict[int, VideoInfo] = {}

_rate_limiter = RateLimiter()

logger = logging.getLogger(__name__)

START_TEXT = (
    "Привет! Я помогу скачать видео или аудио с YouTube.\n\n"
    "• Отправь ссылку на видео — покажу доступные форматы.\n"
    "• Отправь ссылку на канал — сохраню его в «📺 Мои подписки»."
)

HELP_TEXT = (
    "Как пользоваться:\n"
    "1. Отправь ссылку на видео YouTube — выбери формат и получи файл.\n"
    "2. Отправь ссылку на канал YouTube — я сохраню его в подписках.\n"
    "3. В «📺 Мои подписки» можно вернуться к сохранённым каналам.\n\n"
    "Команды:\n"
    "/start — начать\n"
    "/help — эта справка\n"
    "/subscriptions — мои подписки"
)


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    """Reply to the /start command with the main menu."""
    _touch_user(message.from_user)
    await message.answer(START_TEXT, reply_markup=build_main_menu_keyboard())


@router.message(Command("help"))
@router.message(F.text == MENU_HELP)
async def handle_help(message: Message) -> None:
    """Reply to the /help command with the main menu."""
    await message.answer(HELP_TEXT, reply_markup=build_main_menu_keyboard())


@router.message(F.text == MENU_DOWNLOAD)
async def handle_menu_download(message: Message) -> None:
    """Hint the user to send a video link."""
    await message.answer(DOWNLOAD_HINT_TEXT)


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

DOWNLOAD_HINT_TEXT = (
    "Отправь ссылку на видео YouTube — покажу доступные форматы.\n"
    "Ссылку на канал можно сохранить в «📺 Мои подписки»."
)

SUBS_EMPTY_TEXT = (
    "У тебя пока нет подписок.\n"
    "Отправь ссылку на канал YouTube, например https://www.youtube.com/@NASA — "
    "я сохраню его в «📺 Мои подписки»."
)

SUBS_TITLE_TEXT = "Твои подписки:"

CHANNEL_ADDED_TEXT = "Канал «{title}» сохранён в подписках."

CHANNEL_EXISTS_TEXT = "Канал «{title}» уже в подписках."

CHANNEL_FAILED_TEXT = (
    "Не удалось получить информацию о канале. Проверь ссылку и попробуй снова."
)

SUBSCRIPTION_EXPIRED_TEXT = (
    "Не удалось найти подписку. Открой список «📺 Мои подписки» заново."
)

SUBSCRIPTION_DELETED_TEXT = "Подписка удалена."

_UNSAFE_FILENAME = re.compile(r'[\\/:*?"<>|\x00-\x1f]+')
_MAX_FILENAME_LENGTH = 64


def document_filename(title: str, suffix: str) -> str:
    """Build a safe Telegram document name from the video title."""
    name = _UNSAFE_FILENAME.sub(" ", title)
    name = " ".join(name.split()).strip(" .")
    name = name[:_MAX_FILENAME_LENGTH].rstrip(" .") or "video"
    return f"{name}{suffix}"


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


def _callback_id(data: str | None, prefix: str) -> int | None:
    """Parse an integer subscription id out of callback data."""
    raw = (data or "")[len(prefix) :]
    try:
        return int(raw)
    except ValueError:
        return None


def _list_saved_channels(user: TelegramUser | None) -> list[tuple[int, str]]:
    """Return ``(id, title)`` pairs for the channels saved by ``user``."""
    if user is None:
        return []
    with session_scope() as session:
        return [(sub.id, sub.title) for sub in list_subscriptions(session, user.id)]


def _save_channel(
    user: TelegramUser | None,
    channel: ChannelInfo,
) -> tuple[int, bool]:
    """Persist a channel for ``user``; return its id and whether it is new."""
    if user is None:
        return 0, False
    with session_scope() as session:
        subscription, created = add_subscription(
            session,
            user.id,
            user.username,
            channel_id=channel.channel_id,
            url=channel.url,
            title=channel.title,
        )
        return subscription.id, created


def _get_channel(
    user: TelegramUser | None,
    subscription_id: int,
) -> tuple[str, str] | None:
    """Return ``(title, url)`` of a saved channel or ``None``."""
    if user is None:
        return None
    with session_scope() as session:
        subscription = get_subscription(session, user.id, subscription_id)
        if subscription is None:
            return None
        return subscription.title, subscription.url


def _delete_channel(user: TelegramUser | None, subscription_id: int) -> bool:
    """Delete a saved channel; return whether it existed."""
    if user is None:
        return False
    with session_scope() as session:
        return remove_subscription(session, user.id, subscription_id)


async def _handle_channel_link(
    message: Message,
    user: TelegramUser | None,
    text: str,
) -> None:
    """Look up a channel, save it and confirm."""
    await message.answer(PROCESSING_TEXT)
    try:
        channel = await fetch_channel_info(text)
    except ExtractionError:
        await message.answer(CHANNEL_FAILED_TEXT)
        return
    subscription_id, created = _save_channel(user, channel)
    template = CHANNEL_ADDED_TEXT if created else CHANNEL_EXISTS_TEXT
    await message.answer(
        template.format(title=channel.title),
        reply_markup=build_subscription_actions_keyboard(subscription_id),
    )


@router.message(Command("subscriptions"))
@router.message(F.text == MENU_SUBSCRIPTIONS)
async def handle_subscriptions(message: Message) -> None:
    """List the channels saved by the user."""
    subscriptions = _list_saved_channels(message.from_user)
    if not subscriptions:
        await message.answer(SUBS_EMPTY_TEXT)
        return
    await message.answer(
        SUBS_TITLE_TEXT,
        reply_markup=build_subscriptions_keyboard(subscriptions),
    )


@router.callback_query(F.data.startswith(SUBSCRIPTION_CALLBACK_PREFIX))
async def handle_subscription_open(callback: CallbackQuery) -> None:
    """Show a saved channel with its actions."""
    await callback.answer()
    message = callback.message
    if message is None:
        return
    subscription_id = _callback_id(callback.data, SUBSCRIPTION_CALLBACK_PREFIX)
    channel = (
        None
        if subscription_id is None
        else _get_channel(callback.from_user, subscription_id)
    )
    if channel is None:
        await message.answer(SUBSCRIPTION_EXPIRED_TEXT)
        return
    title, url = channel
    await message.answer(
        f"{title}\n{url}",
        reply_markup=build_subscription_actions_keyboard(subscription_id),
    )


@router.callback_query(F.data.startswith(SUBSCRIPTION_DELETE_PREFIX))
async def handle_subscription_delete(callback: CallbackQuery) -> None:
    """Delete a saved channel."""
    await callback.answer()
    message = callback.message
    if message is None:
        return
    subscription_id = _callback_id(callback.data, SUBSCRIPTION_DELETE_PREFIX)
    removed = subscription_id is not None and _delete_channel(
        callback.from_user, subscription_id
    )
    text = SUBSCRIPTION_DELETED_TEXT if removed else SUBSCRIPTION_EXPIRED_TEXT
    try:
        await message.edit_text(text)
    except TelegramBadRequest:
        await message.answer(text)


async def _send_video_summary(message: Message, info: VideoInfo) -> None:
    """Send the thumbnail with the caption and format keyboard."""
    caption = format_info_message(info)
    keyboard = build_formats_keyboard(info.formats)
    if info.thumbnail:
        try:
            await message.answer_photo(
                photo=info.thumbnail,
                caption=caption,
                reply_markup=keyboard,
            )
            return
        except TelegramBadRequest:
            logger.warning("Could not send thumbnail, falling back to text")
    await message.answer(caption, reply_markup=keyboard)


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
    if is_channel_url(text):
        await _handle_channel_link(message, user, text)
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
    info = replace(info, formats=select_formats(info.formats))
    _last_video[message.chat.id] = info
    await _send_video_summary(message, info)


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
            path = await fetch_format(
                info.url,
                format_id,
                tmp,
                merge_audio=fmt.has_video and not fmt.has_audio,
                audio_only=fmt.ext == "mp3",
            )
            if path.stat().st_size > MAX_FILE_SIZE:
                _record_download(user, info, fmt, STATUS_TOO_LARGE)
                await message.answer(TOO_LARGE_TEXT)
                return
            await message.answer_document(
                FSInputFile(
                    path,
                    filename=document_filename(info.title, path.suffix),
                )
            )
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
