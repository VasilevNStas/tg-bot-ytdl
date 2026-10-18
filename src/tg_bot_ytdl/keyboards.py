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
    name = fmt.resolution or fmt.note or fmt.ext
    label = f"{name} · {fmt.ext}"
    size = format_filesize(fmt.filesize)
    if size:
        label = f"{label} · {size}"
    return label


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
