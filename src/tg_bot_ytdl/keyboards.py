# SPDX-FileCopyrightText: Copyright (c) 2026 VasilevNStas
# SPDX-License-Identifier: MIT
"""Inline keyboards for format selection."""

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from tg_bot_ytdl.extractor import VideoFormat

CALLBACK_PREFIX = "fmt:"
MAX_FORMAT_BUTTONS = 20


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


def _is_playable(fmt: VideoFormat) -> bool:
    """Return ``True`` for real audio/video streams (not storyboards)."""
    if fmt.ext == "mhtml" or fmt.format_id.startswith("sb"):
        return False
    return fmt.has_video or fmt.has_audio


def select_formats(formats: list[VideoFormat]) -> list[VideoFormat]:
    """Filter, deduplicate and rank formats for display in the keyboard."""
    best: dict[tuple[bool, bool, int], VideoFormat] = {}
    for fmt in formats:
        if not _is_playable(fmt):
            continue
        key = (fmt.has_video, fmt.has_audio, fmt.height or 0)
        current = best.get(key)
        if current is None or (fmt.filesize or 0) > (current.filesize or 0):
            best[key] = fmt
    ordered = sorted(
        best.values(),
        key=lambda fmt: (
            fmt.has_video,
            fmt.has_audio,
            fmt.height or 0,
            fmt.filesize or 0,
        ),
        reverse=True,
    )
    return ordered[:MAX_FORMAT_BUTTONS]


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
