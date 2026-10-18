# SPDX-FileCopyrightText: Copyright (c) 2026 VasilevNStas
# SPDX-License-Identifier: MIT
"""Inline keyboards for format selection."""

from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from tg_bot_ytdl.channels import (
    SECTION_SHORTS,
    SECTION_STREAMS,
    SECTION_VIDEOS,
)
from tg_bot_ytdl.extractor import VideoFormat

CALLBACK_PREFIX = "fmt:"
MAX_FORMAT_BUTTONS = 20
MP3_FORMAT_ID = "mp3"

MENU_DOWNLOAD = "🔗 Скачать по ссылке"
MENU_SUBSCRIPTIONS = "📺 Мои подписки"
MENU_HELP = "ℹ️ Помощь"

SUBSCRIPTION_CALLBACK_PREFIX = "sub:"
SUBSCRIPTION_DELETE_PREFIX = "subdel:"

SECTION_CALLBACK_PREFIX = "sec:"
VIDEO_CALLBACK_PREFIX = "dl:"
VIDEO_BUTTON_TEXT = "⬇️ Скачать"

SECTION_LABELS: tuple[tuple[str, str], ...] = (
    (SECTION_VIDEOS, "🎬 Видео"),
    (SECTION_SHORTS, "📱 Шортс"),
    (SECTION_STREAMS, "🔴 Трансляции"),
)

_MAX_BUTTON_TITLE = 40


def build_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Build the persistent main menu reply keyboard."""
    builder = ReplyKeyboardBuilder()
    builder.button(text=MENU_DOWNLOAD)
    builder.button(text=MENU_SUBSCRIPTIONS)
    builder.button(text=MENU_HELP)
    builder.adjust(2, 1)
    return builder.as_markup(
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Ссылка на видео или канал",
    )


def channel_button_label(title: str) -> str:
    """Build a compact label for a saved channel button."""
    clean = " ".join(title.split())
    if len(clean) > _MAX_BUTTON_TITLE:
        clean = clean[: _MAX_BUTTON_TITLE - 1].rstrip() + "…"
    return clean or "Канал"


def build_subscriptions_keyboard(
    subscriptions: list[tuple[int, str]],
) -> InlineKeyboardMarkup | None:
    """Build a keyboard with one button per saved channel."""
    if not subscriptions:
        return None
    builder = InlineKeyboardBuilder()
    for subscription_id, title in subscriptions:
        builder.button(
            text=channel_button_label(title),
            callback_data=f"{SUBSCRIPTION_CALLBACK_PREFIX}{subscription_id}",
        )
    builder.adjust(1)
    return builder.as_markup()


def build_subscription_actions_keyboard(
    subscription_id: int,
) -> InlineKeyboardMarkup:
    """Build the actions keyboard for a single saved channel."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="❌ Удалить",
        callback_data=f"{SUBSCRIPTION_DELETE_PREFIX}{subscription_id}",
    )
    builder.adjust(1)
    return builder.as_markup()


def build_channel_sections_keyboard(
    subscription_id: int,
) -> InlineKeyboardMarkup:
    """Build the section picker for a saved channel."""
    builder = InlineKeyboardBuilder()
    for section, label in SECTION_LABELS:
        builder.button(
            text=label,
            callback_data=f"{SECTION_CALLBACK_PREFIX}{subscription_id}:{section}",
        )
    builder.button(
        text="❌ Удалить",
        callback_data=f"{SUBSCRIPTION_DELETE_PREFIX}{subscription_id}",
    )
    builder.adjust(1)
    return builder.as_markup()


def build_video_keyboard(video_id: str) -> InlineKeyboardMarkup:
    """Build the download button shown under a video preview."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text=VIDEO_BUTTON_TEXT,
        callback_data=f"{VIDEO_CALLBACK_PREFIX}{video_id}",
    )
    builder.adjust(1)
    return builder.as_markup()


def format_filesize(size: int | None) -> str:
    """Format a byte size as a human-readable string (empty for unknown)."""
    if not size:
        return ""
    megabytes = size / (1024 * 1024)
    if megabytes < 1:
        return f"{size / 1024:.0f} KB"
    return f"{megabytes:.1f} MB"


def format_button_label(fmt: VideoFormat) -> str:
    """Build a compact label for a single format button."""
    if fmt.has_audio and not fmt.has_video:
        name = f"аудио {fmt.note}" if fmt.note else "аудио"
    else:
        name = fmt.resolution or fmt.note or fmt.ext
    label = f"{name} · {fmt.ext}"
    size = format_filesize(fmt.filesize)
    if size:
        label = f"{label} · {size}"
    return label


def select_formats(formats: list[VideoFormat]) -> list[VideoFormat]:
    """Pick MP4 video qualities and add a single MP3 audio option."""
    best: dict[int, VideoFormat] = {}
    for fmt in formats:
        if fmt.ext != "mp4" or not fmt.has_video or not fmt.height:
            continue
        current = best.get(fmt.height)
        if current is None or (fmt.filesize or 0) > (current.filesize or 0):
            best[fmt.height] = fmt

    videos = sorted(best.values(), key=lambda fmt: fmt.height or 0, reverse=True)
    selected = videos[: MAX_FORMAT_BUTTONS - 1]
    if selected or any(fmt.has_audio for fmt in formats):
        selected.append(
            VideoFormat(
                format_id=MP3_FORMAT_ID,
                ext="mp3",
                resolution=None,
                filesize=None,
                note=None,
                has_audio=True,
            )
        )
    return selected


def build_formats_keyboard(
    formats: list[VideoFormat],
) -> InlineKeyboardMarkup | None:
    """Build an inline keyboard of formats, or ``None`` when there are none."""
    if not formats:
        return None
    builder = InlineKeyboardBuilder()
    for fmt in formats[:MAX_FORMAT_BUTTONS]:
        builder.button(
            text=format_button_label(fmt),
            callback_data=f"{CALLBACK_PREFIX}{fmt.format_id}",
        )
    builder.adjust(1)
    return builder.as_markup()
