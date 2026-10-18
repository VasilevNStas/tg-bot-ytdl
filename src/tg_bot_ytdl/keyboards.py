# SPDX-FileCopyrightText: Copyright (c) 2026 VasilevNStas
# SPDX-License-Identifier: MIT
"""Inline keyboards for format selection."""

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from tg_bot_ytdl.extractor import VideoFormat

CALLBACK_PREFIX = "fmt:"
MAX_FORMAT_BUTTONS = 20
MP3_FORMAT_ID = "mp3"


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
