# SPDX-FileCopyrightText: Copyright (c) 2026 VasilevNStas
# SPDX-License-Identifier: MIT
"""Tests for inline format keyboards."""

import pytest

from tg_bot_ytdl.extractor import VideoFormat
from tg_bot_ytdl.keyboards import (
    CALLBACK_PREFIX,
    MAX_FORMAT_BUTTONS,
    build_formats_keyboard,
    format_button_label,
    format_filesize,
)


def _fmt(
    format_id: str = "137",
    ext: str = "mp4",
    resolution: str | None = "1280x720",
    filesize: int | None = None,
    note: str | None = None,
) -> VideoFormat:
    return VideoFormat(
        format_id=format_id,
        ext=ext,
        resolution=resolution,
        filesize=filesize,
        note=note,
    )


def test_build_returns_none_for_empty() -> None:
    assert build_formats_keyboard([]) is None


def test_build_creates_button_per_format() -> None:
    markup = build_formats_keyboard([_fmt("137"), _fmt("22")])
    assert markup is not None
    assert len(markup.inline_keyboard) == 2


def test_button_callback_data_has_prefix() -> None:
    markup = build_formats_keyboard([_fmt("137")])
    assert markup is not None
    button = markup.inline_keyboard[0][0]
    assert button.callback_data == f"{CALLBACK_PREFIX}137"


def test_build_limits_button_count() -> None:
    formats = [_fmt(format_id=str(i)) for i in range(MAX_FORMAT_BUTTONS + 5)]
    markup = build_formats_keyboard(formats)
    assert markup is not None
    assert len(markup.inline_keyboard) == MAX_FORMAT_BUTTONS


def test_button_label_includes_resolution_ext_and_size() -> None:
    label = format_button_label(_fmt(filesize=5 * 1024 * 1024))
    assert "1280x720" in label
    assert "mp4" in label
    assert "5.0 MB" in label


def test_button_label_falls_back_to_note() -> None:
    label = format_button_label(_fmt(resolution=None, note="audio only"))
    assert label.startswith("audio only")


@pytest.mark.parametrize(
    ("size", "expected"),
    [(None, ""), (0, ""), (512 * 1024, "512 KB"), (2 * 1024 * 1024, "2.0 MB")],
)
def test_format_filesize(size: int | None, expected: str) -> None:
    assert format_filesize(size) == expected
