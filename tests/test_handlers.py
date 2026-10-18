# SPDX-FileCopyrightText: Copyright (c) 2026 VasilevNStas
# SPDX-License-Identifier: MIT
"""Tests for command and link handlers."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from tg_bot_ytdl import db, handlers
from tg_bot_ytdl.downloader import DownloadError
from tg_bot_ytdl.extractor import ExtractionError, VideoFormat, VideoInfo
from tg_bot_ytdl.handlers import (
    DOWNLOAD_FAILED_TEXT,
    EXTRACTION_FAILED_TEXT,
    FORMAT_SELECTED_TEXT,
    HELP_TEXT,
    NOT_A_LINK_TEXT,
    PROCESSING_TEXT,
    RATE_LIMITED_TEXT,
    SELECTION_EXPIRED_TEXT,
    START_TEXT,
    TOO_LARGE_TEXT,
    UNEXPECTED_ERROR_TEXT,
    format_duration,
    handle_error,
    handle_format_selected,
    handle_help,
    handle_link,
    handle_start,
)
from tg_bot_ytdl.models import DownloadRequest, User


@pytest.fixture(autouse=True)
def _clear_last_video() -> None:
    handlers._last_video.clear()
    handlers._rate_limiter.reset()


def _message(text: str, user_id: int = 1) -> AsyncMock:
    message = AsyncMock()
    message.text = text
    message.from_user.id = user_id
    message.from_user.username = None
    message.chat.id = user_id
    return message


def _callback(chat_id: int, data: str) -> AsyncMock:
    callback = AsyncMock()
    callback.data = data
    callback.from_user.id = chat_id
    callback.from_user.username = None
    callback.message.chat.id = chat_id
    return callback


def _video_format(filesize: int | None = None) -> VideoFormat:
    return VideoFormat(
        format_id="137",
        ext="mp4",
        resolution="1280x720",
        filesize=filesize,
        note=None,
    )


async def test_handle_start_replies() -> None:
    message = _message("/start")
    await handle_start(message)
    message.answer.assert_awaited_once_with(START_TEXT)


async def test_handle_start_registers_user() -> None:
    message = _message("/start", user_id=55)
    await handle_start(message)
    with db.session_scope() as session:
        user = session.scalar(select(User).where(User.telegram_id == 55))
        assert user is not None


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
    callback = _callback(1, "fmt:137")
    await handle_format_selected(callback)
    callback.answer.assert_awaited_once_with(FORMAT_SELECTED_TEXT)
    callback.message.answer.assert_awaited_once_with(SELECTION_EXPIRED_TEXT)


async def test_handle_format_selected_downloads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    info = VideoInfo(
        url="https://youtu.be/x",
        title="Test Video",
        duration=65,
        uploader="Test Channel",
        formats=[_video_format()],
    )
    handlers._last_video[1] = info

    async def _fake_download(url: str, format_id: str, dest_dir: object) -> Path:
        path = Path(str(dest_dir)) / f"{format_id}.mp4"
        path.write_bytes(b"data")
        return path

    monkeypatch.setattr(handlers, "fetch_format", _fake_download)
    callback = _callback(1, "fmt:137")

    await handle_format_selected(callback)

    callback.message.answer.assert_any_await(handlers.DOWNLOADING_TEXT)
    callback.message.answer_document.assert_awaited_once()


async def test_handle_format_selected_records_download(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    info = VideoInfo(
        url="https://youtu.be/x",
        title="Test Video",
        duration=65,
        uploader="Test Channel",
        formats=[_video_format()],
    )
    handlers._last_video[1] = info

    async def _fake_download(url: str, format_id: str, dest_dir: object) -> Path:
        path = Path(str(dest_dir)) / f"{format_id}.mp4"
        path.write_bytes(b"data")
        return path

    monkeypatch.setattr(handlers, "fetch_format", _fake_download)
    callback = _callback(1, "fmt:137")

    await handle_format_selected(callback)

    with db.session_scope() as session:
        request = session.scalar(select(DownloadRequest))
        assert request is not None
        assert request.status == "sent"
        assert request.format_id == "137"


async def test_handle_format_selected_rejects_large_known_size(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    info = VideoInfo(
        url="https://youtu.be/x",
        title="Test Video",
        duration=65,
        uploader="Test Channel",
        formats=[_video_format(filesize=handlers.MAX_FILE_SIZE + 1)],
    )
    handlers._last_video[1] = info

    async def _unused_download(*args: object, **kwargs: object) -> Path:
        raise AssertionError("download should not be called")

    monkeypatch.setattr(handlers, "fetch_format", _unused_download)
    callback = _callback(1, "fmt:137")

    await handle_format_selected(callback)

    callback.message.answer.assert_awaited_once_with(TOO_LARGE_TEXT)
    callback.message.answer_document.assert_not_awaited()


async def test_handle_format_selected_rejects_large_actual_size(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    info = VideoInfo(
        url="https://youtu.be/x",
        title="Test Video",
        duration=65,
        uploader="Test Channel",
        formats=[_video_format()],
    )
    handlers._last_video[1] = info
    monkeypatch.setattr(handlers, "MAX_FILE_SIZE", 2)

    async def _fake_download(url: str, format_id: str, dest_dir: object) -> Path:
        path = Path(str(dest_dir)) / f"{format_id}.mp4"
        path.write_bytes(b"too-big")
        return path

    monkeypatch.setattr(handlers, "fetch_format", _fake_download)
    callback = _callback(1, "fmt:137")

    await handle_format_selected(callback)

    callback.message.answer.assert_any_await(TOO_LARGE_TEXT)
    callback.message.answer_document.assert_not_awaited()


async def test_handle_format_selected_download_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    info = VideoInfo(
        url="https://youtu.be/x",
        title="Test Video",
        duration=65,
        uploader="Test Channel",
        formats=[_video_format()],
    )
    handlers._last_video[1] = info
    monkeypatch.setattr(
        handlers,
        "fetch_format",
        AsyncMock(side_effect=DownloadError("boom")),
    )
    callback = _callback(1, "fmt:137")

    await handle_format_selected(callback)

    callback.message.answer.assert_any_await(DOWNLOAD_FAILED_TEXT)
    callback.message.answer_document.assert_not_awaited()


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


async def test_handle_link_rate_limits_user(
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

    first = _message("https://youtu.be/x", user_id=7)
    await handle_link(first)
    second = _message("https://youtu.be/x", user_id=7)

    await handle_link(second)

    second.answer.assert_awaited_once_with(RATE_LIMITED_TEXT)


async def test_handle_link_without_user() -> None:
    message = AsyncMock()
    message.text = "привет"
    message.from_user = None
    message.chat.id = 1

    await handle_link(message)

    message.answer.assert_awaited_once_with(NOT_A_LINK_TEXT)


async def test_handle_format_selected_without_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    info = VideoInfo(
        url="https://youtu.be/x",
        title="Test Video",
        duration=65,
        uploader="Test Channel",
        formats=[_video_format()],
    )
    handlers._last_video[1] = info

    async def _fake_download(url: str, format_id: str, dest_dir: object) -> Path:
        path = Path(str(dest_dir)) / f"{format_id}.mp4"
        path.write_bytes(b"data")
        return path

    monkeypatch.setattr(handlers, "fetch_format", _fake_download)
    callback = _callback(1, "fmt:137")
    callback.from_user = None

    await handle_format_selected(callback)

    callback.message.answer_document.assert_awaited_once()


async def test_handle_format_selected_without_message() -> None:
    callback = _callback(1, "fmt:137")
    callback.message = None

    await handle_format_selected(callback)

    callback.answer.assert_awaited_once_with(FORMAT_SELECTED_TEXT)


async def test_handle_error_notifies_user() -> None:
    message = AsyncMock()
    event = SimpleNamespace(
        exception=ValueError("boom"),
        update=SimpleNamespace(message=message, callback_query=None),
    )

    result = await handle_error(event)

    assert result is True
    message.answer.assert_awaited_once_with(UNEXPECTED_ERROR_TEXT)


async def test_handle_error_uses_callback_message() -> None:
    message = AsyncMock()
    event = SimpleNamespace(
        exception=ValueError("boom"),
        update=SimpleNamespace(
            message=None,
            callback_query=SimpleNamespace(message=message),
        ),
    )

    result = await handle_error(event)

    assert result is True
    message.answer.assert_awaited_once_with(UNEXPECTED_ERROR_TEXT)


async def test_handle_error_without_message() -> None:
    event = SimpleNamespace(
        exception=ValueError("boom"),
        update=SimpleNamespace(message=None, callback_query=None),
    )

    assert await handle_error(event) is True


async def test_handle_error_swallows_notify_failure() -> None:
    message = AsyncMock()
    message.answer.side_effect = RuntimeError("nope")
    event = SimpleNamespace(
        exception=ValueError("boom"),
        update=SimpleNamespace(message=message, callback_query=None),
    )

    assert await handle_error(event) is True


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [(None, "—"), (0, "—"), (65, "1:05"), (3661, "1:01:01")],
)
def test_format_duration(seconds: int | None, expected: str) -> None:
    assert format_duration(seconds) == expected
