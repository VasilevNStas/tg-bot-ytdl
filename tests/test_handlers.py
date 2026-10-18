# SPDX-FileCopyrightText: Copyright (c) 2026 VasilevNStas
# SPDX-License-Identifier: MIT
"""Tests for command and link handlers."""

from unittest.mock import AsyncMock

import pytest

from tg_bot_ytdl import handlers
from tg_bot_ytdl.extractor import ExtractionError, VideoFormat, VideoInfo
from tg_bot_ytdl.handlers import (
    EXTRACTION_FAILED_TEXT,
    FORMAT_SELECTED_TEXT,
    HELP_TEXT,
    NOT_A_LINK_TEXT,
    PROCESSING_TEXT,
    START_TEXT,
    format_duration,
    handle_format_selected,
    handle_help,
    handle_link,
    handle_start,
)


def _message(text: str) -> AsyncMock:
    message = AsyncMock()
    message.text = text
    return message


async def test_handle_start_replies() -> None:
    message = _message("/start")
    await handle_start(message)
    message.answer.assert_awaited_once_with(START_TEXT)


async def test_handle_help_replies() -> None:
    message = _message("/help")
    await handle_help(message)
    message.answer.assert_awaited_once_with(HELP_TEXT)


async def test_handle_link_rejects_non_link() -> None:
    message = _message("привет")
    await handle_link(message)
    message.answer.assert_awaited_once_with(NOT_A_LINK_TEXT)


async def test_handle_link_ignores_commands() -> None:
    message = _message("/unknown")
    await handle_link(message)
    message.answer.assert_not_awaited()


async def test_handle_link_reports_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    info = VideoInfo(
        url="https://youtu.be/x",
        title="Test Video",
        duration=65,
        uploader="Test Channel",
        formats=[],
    )
    monkeypatch.setattr(handlers, "fetch_video_info", AsyncMock(return_value=info))
    message = _message("https://youtu.be/x")

    await handle_link(message)

    assert message.answer.await_count == 2
    message.answer.assert_any_await(PROCESSING_TEXT)
    message.answer.assert_any_await(
        handlers.format_info_message(info), reply_markup=None
    )


async def test_handle_link_attaches_formats_keyboard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fmt = VideoFormat(
        format_id="137",
        ext="mp4",
        resolution="1280x720",
        filesize=None,
        note=None,
    )
    info = VideoInfo(
        url="https://youtu.be/x",
        title="Test Video",
        duration=65,
        uploader="Test Channel",
        formats=[fmt],
    )
    monkeypatch.setattr(handlers, "fetch_video_info", AsyncMock(return_value=info))
    message = _message("https://youtu.be/x")

    await handle_link(message)

    markup = message.answer.await_args.kwargs["reply_markup"]
    assert markup is not None
    assert markup.inline_keyboard[0][0].callback_data == "fmt:137"


async def test_handle_format_selected_answers() -> None:
    callback = AsyncMock()
    await handle_format_selected(callback)
    callback.answer.assert_awaited_once_with(FORMAT_SELECTED_TEXT)


async def test_handle_link_handles_extraction_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        handlers,
        "fetch_video_info",
        AsyncMock(side_effect=ExtractionError("boom")),
    )
    message = _message("https://youtu.be/x")

    await handle_link(message)

    message.answer.assert_any_await(EXTRACTION_FAILED_TEXT)


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [(None, "—"), (0, "—"), (65, "1:05"), (3661, "1:01:01")],
)
def test_format_duration(seconds: int | None, expected: str) -> None:
    assert format_duration(seconds) == expected
