# SPDX-FileCopyrightText: Copyright (c) 2026 VasilevNStas
# SPDX-License-Identifier: MIT
"""Tests for command and link handlers."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy import select

from tg_bot_ytdl import db, handlers
from tg_bot_ytdl.channels import ChannelInfo, ChannelVideo
from tg_bot_ytdl.downloader import DownloadError
from tg_bot_ytdl.extractor import ExtractionError, VideoFormat, VideoInfo
from tg_bot_ytdl.handlers import (
    CHANNEL_ADDED_TEXT,
    CHANNEL_EXISTS_TEXT,
    CHANNEL_FAILED_TEXT,
    DOWNLOAD_FAILED_TEXT,
    DOWNLOAD_HINT_TEXT,
    EXTRACTION_FAILED_TEXT,
    FORMAT_SELECTED_TEXT,
    FORMATS_PREPARING_TEXT,
    HELP_TEXT,
    NOT_A_LINK_TEXT,
    PROCESSING_TEXT,
    RATE_LIMITED_TEXT,
    SECTION_EMPTY_TEXT,
    SECTION_EXPIRED_TEXT,
    SECTION_FAILED_TEXT,
    SECTION_LIST_TITLE_TEXT,
    SECTION_LOADING_TEXT,
    SELECTION_EXPIRED_TEXT,
    START_TEXT,
    SUBS_EMPTY_TEXT,
    SUBSCRIPTION_DELETED_TEXT,
    SUBSCRIPTION_EXPIRED_TEXT,
    TOO_LARGE_TEXT,
    UNEXPECTED_ERROR_TEXT,
    format_duration,
    handle_error,
    handle_format_selected,
    handle_help,
    handle_link,
    handle_menu_download,
    handle_section_selected,
    handle_start,
    handle_subscription_delete,
    handle_subscription_open,
    handle_subscriptions,
    handle_video_selected,
)
from tg_bot_ytdl.keyboards import MENU_DOWNLOAD, MENU_SUBSCRIPTIONS
from tg_bot_ytdl.models import DownloadRequest, Subscription, User
from tg_bot_ytdl.repository import add_subscription


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
        height=720,
        has_video=True,
        has_audio=True,
    )


async def test_handle_start_replies() -> None:
    message = _message("/start")
    await handle_start(message)
    assert message.answer.await_args.args[0] == START_TEXT
    assert message.answer.await_args.kwargs["reply_markup"] is not None


async def test_handle_start_registers_user() -> None:
    message = _message("/start", user_id=55)
    await handle_start(message)
    with db.session_scope() as session:
        user = session.scalar(select(User).where(User.telegram_id == 55))
        assert user is not None


async def test_handle_help_replies() -> None:
    message = _message("/help")
    await handle_help(message)
    assert message.answer.await_args.args[0] == HELP_TEXT
    assert message.answer.await_args.kwargs["reply_markup"] is not None


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
        height=720,
        has_video=True,
        has_audio=True,
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

    async def _fake_download(
        url: str,
        format_id: str,
        dest_dir: object,
        *,
        merge_audio: bool = False,
        audio_only: bool = False,
    ) -> Path:
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

    async def _fake_download(
        url: str,
        format_id: str,
        dest_dir: object,
        *,
        merge_audio: bool = False,
        audio_only: bool = False,
    ) -> Path:
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

    async def _fake_download(
        url: str,
        format_id: str,
        dest_dir: object,
        *,
        merge_audio: bool = False,
        audio_only: bool = False,
    ) -> Path:
        path = Path(str(dest_dir)) / f"{format_id}.mp4"
        path.write_bytes(b"too-big")
        return path

    monkeypatch.setattr(handlers, "fetch_format", _fake_download)
    callback = _callback(1, "fmt:137")

    await handle_format_selected(callback)

    callback.message.answer.assert_any_await(TOO_LARGE_TEXT)
    callback.message.answer_document.assert_not_awaited()


async def test_handle_format_selected_uses_title_as_filename(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    info = VideoInfo(
        url="https://youtu.be/x",
        title="Rick Astley - Never Gonna Give You Up (Official Video)",
        duration=65,
        uploader="Test Channel",
        formats=[_video_format()],
    )
    handlers._last_video[1] = info

    async def _fake_download(
        url: str,
        format_id: str,
        dest_dir: object,
        *,
        merge_audio: bool = False,
        audio_only: bool = False,
    ) -> Path:
        path = Path(str(dest_dir)) / f"{format_id}.mp4"
        path.write_bytes(b"data")
        return path

    monkeypatch.setattr(handlers, "fetch_format", _fake_download)
    callback = _callback(1, "fmt:137")

    await handle_format_selected(callback)

    document = callback.message.answer_document.await_args.args[0]
    assert (
        document.filename
        == "Rick Astley - Never Gonna Give You Up (Official Video).mp4"
    )


async def test_handle_format_selected_requests_mp3(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audio = VideoFormat(
        format_id="mp3",
        ext="mp3",
        resolution=None,
        filesize=None,
        note=None,
        has_audio=True,
    )
    info = VideoInfo(
        url="https://youtu.be/x",
        title="Test Video",
        duration=65,
        uploader="Test Channel",
        formats=[audio],
    )
    handlers._last_video[1] = info
    captured: dict[str, bool] = {}

    async def _fake_download(
        url: str,
        format_id: str,
        dest_dir: object,
        *,
        merge_audio: bool = False,
        audio_only: bool = False,
    ) -> Path:
        captured["audio_only"] = audio_only
        path = Path(str(dest_dir)) / f"{format_id}.mp3"
        path.write_bytes(b"data")
        return path

    monkeypatch.setattr(handlers, "fetch_format", _fake_download)
    callback = _callback(1, "fmt:mp3")

    await handle_format_selected(callback)

    assert captured["audio_only"] is True
    document = callback.message.answer_document.await_args.args[0]
    assert document.filename == "Test Video.mp3"


def test_document_filename_sanitizes_title() -> None:
    assert handlers.document_filename('a/b:c*?"<>|', ".mp4") == "a b c.mp4"
    assert handlers.document_filename("   ", ".mp3") == "video.mp3"
    assert len(handlers.document_filename("x" * 200, ".mp4")) == 68


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

    async def _fake_download(
        url: str,
        format_id: str,
        dest_dir: object,
        *,
        merge_audio: bool = False,
        audio_only: bool = False,
    ) -> Path:
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


async def test_handle_link_sends_thumbnail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    info = VideoInfo(
        url="https://youtu.be/x",
        title="Test Video",
        duration=65,
        uploader="Test Channel",
        formats=[_video_format()],
        thumbnail="https://i.ytimg.com/vi/x/hqdefault.jpg",
    )
    monkeypatch.setattr(handlers, "fetch_video_info", AsyncMock(return_value=info))
    message = _message("https://youtu.be/x")

    await handle_link(message)

    message.answer_photo.assert_awaited_once()
    assert message.answer_photo.await_args.kwargs["photo"] == info.thumbnail
    message.answer.assert_awaited_once_with(PROCESSING_TEXT)


async def test_handle_link_falls_back_when_thumbnail_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    info = VideoInfo(
        url="https://youtu.be/x",
        title="Test Video",
        duration=65,
        uploader="Test Channel",
        formats=[_video_format()],
        thumbnail="https://i.ytimg.com/vi/x/hqdefault.jpg",
    )
    monkeypatch.setattr(handlers, "fetch_video_info", AsyncMock(return_value=info))
    message = _message("https://youtu.be/x")
    message.answer_photo.side_effect = TelegramBadRequest(
        method=None, message="bad photo"
    )

    await handle_link(message)

    message.answer_photo.assert_awaited_once()
    assert message.answer.await_count == 2
    caption = message.answer.await_args.args[0]
    assert caption.startswith("Test Video")
    assert "Доступно форматов: 2" in caption


async def test_handle_link_reports_curated_format_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    duplicate = _video_format(filesize=1024)
    storyboard = VideoFormat(
        format_id="sb0",
        ext="mhtml",
        resolution=None,
        filesize=None,
        note=None,
    )
    info = VideoInfo(
        url="https://youtu.be/x",
        title="Test Video",
        duration=65,
        uploader="Test Channel",
        formats=[_video_format(), duplicate, storyboard],
    )
    monkeypatch.setattr(handlers, "fetch_video_info", AsyncMock(return_value=info))
    message = _message("https://youtu.be/x")

    await handle_link(message)

    caption = message.answer.await_args.args[0]
    assert "Доступно форматов: 2" in caption
    markup = message.answer.await_args.kwargs["reply_markup"]
    assert len(markup.inline_keyboard) == 2


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [(None, "—"), (0, "—"), (65, "1:05"), (3661, "1:01:01")],
)
def test_format_duration(seconds: int | None, expected: str) -> None:
    assert format_duration(seconds) == expected


def _any_answer(message: AsyncMock, text: str) -> bool:
    return any(
        call.args and call.args[0] == text for call in message.answer.await_args_list
    )


def _channel() -> ChannelInfo:
    return ChannelInfo(
        channel_id="UC123",
        url="https://www.youtube.com/@NASA",
        title="NASA",
    )


async def test_handle_link_saves_channel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        handlers, "fetch_channel_info", AsyncMock(return_value=_channel())
    )
    message = _message("https://www.youtube.com/@NASA", user_id=9)

    await handle_link(message)

    assert _any_answer(message, CHANNEL_ADDED_TEXT.format(title="NASA"))
    with db.session_scope() as session:
        subscription = session.scalar(select(Subscription))
        assert subscription is not None
        assert subscription.channel_id == "UC123"


async def test_handle_link_reports_existing_channel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        handlers, "fetch_channel_info", AsyncMock(return_value=_channel())
    )
    await handle_link(_message("https://www.youtube.com/@NASA", user_id=9))
    handlers._rate_limiter.reset()

    second = _message("https://www.youtube.com/@NASA", user_id=9)
    await handle_link(second)

    assert _any_answer(second, CHANNEL_EXISTS_TEXT.format(title="NASA"))


async def test_handle_link_handles_channel_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        handlers,
        "fetch_channel_info",
        AsyncMock(side_effect=ExtractionError("boom")),
    )
    message = _message("https://www.youtube.com/@NASA", user_id=9)

    await handle_link(message)

    message.answer.assert_any_await(CHANNEL_FAILED_TEXT)


async def test_handle_menu_download_hints() -> None:
    message = _message(MENU_DOWNLOAD)
    await handle_menu_download(message)
    message.answer.assert_awaited_once_with(DOWNLOAD_HINT_TEXT)


async def test_handle_subscriptions_empty() -> None:
    message = _message(MENU_SUBSCRIPTIONS, user_id=11)
    await handle_subscriptions(message)
    message.answer.assert_awaited_once_with(SUBS_EMPTY_TEXT)


async def test_handle_subscriptions_lists_channels() -> None:
    with db.session_scope() as session:
        add_subscription(session, 11, None, channel_id="UC1", url="u", title="NASA")
    message = _message(MENU_SUBSCRIPTIONS, user_id=11)

    await handle_subscriptions(message)

    assert message.answer.await_args.args[0] == handlers.SUBS_TITLE_TEXT
    markup = message.answer.await_args.kwargs["reply_markup"]
    assert markup.inline_keyboard[0][0].callback_data.startswith("sub:")


async def test_handle_subscription_open_shows_channel() -> None:
    with db.session_scope() as session:
        subscription, _ = add_subscription(
            session, 21, None, channel_id="UC1", url="https://x", title="NASA"
        )
        sub_id = subscription.id
    callback = _callback(21, f"sub:{sub_id}")

    await handle_subscription_open(callback)

    callback.answer.assert_awaited_once()
    assert "NASA" in callback.message.answer.await_args.args[0]


async def test_handle_subscription_open_expired() -> None:
    callback = _callback(21, "sub:999")

    await handle_subscription_open(callback)

    callback.message.answer.assert_awaited_once_with(SUBSCRIPTION_EXPIRED_TEXT)


async def test_handle_subscription_delete_removes() -> None:
    with db.session_scope() as session:
        subscription, _ = add_subscription(
            session, 21, None, channel_id="UC1", url="https://x", title="NASA"
        )
        sub_id = subscription.id
    callback = _callback(21, f"subdel:{sub_id}")

    await handle_subscription_delete(callback)

    callback.message.edit_text.assert_awaited_once_with(SUBSCRIPTION_DELETED_TEXT)
    with db.session_scope() as session:
        assert session.scalar(select(Subscription)) is None


async def test_handle_subscription_delete_expired() -> None:
    callback = _callback(21, "subdel:999")

    await handle_subscription_delete(callback)

    callback.message.edit_text.assert_awaited_once_with(SUBSCRIPTION_EXPIRED_TEXT)


async def test_handle_subscription_delete_falls_back_on_edit_error() -> None:
    with db.session_scope() as session:
        subscription, _ = add_subscription(
            session, 21, None, channel_id="UC1", url="https://x", title="NASA"
        )
        sub_id = subscription.id
    callback = _callback(21, f"subdel:{sub_id}")
    callback.message.edit_text.side_effect = TelegramBadRequest(
        method=None, message="bad"
    )

    await handle_subscription_delete(callback)

    callback.message.answer.assert_awaited_once_with(SUBSCRIPTION_DELETED_TEXT)


async def test_handle_subscription_open_without_message() -> None:
    callback = _callback(21, "sub:1")
    callback.message = None

    await handle_subscription_open(callback)

    callback.answer.assert_awaited_once()


def _channel_video(video_id: str = "dQw4w9WgXcQ") -> ChannelVideo:
    return ChannelVideo(
        video_id=video_id,
        title="Rick Astley",
        url=f"https://www.youtube.com/watch?v={video_id}",
        duration=213,
    )


def _saved_subscription(user_id: int = 31) -> int:
    with db.session_scope() as session:
        subscription, _ = add_subscription(
            session,
            user_id,
            None,
            channel_id="UC1",
            url="https://www.youtube.com/@NASA",
            title="NASA",
        )
        return subscription.id


async def test_handle_section_selected_sends_cards(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    video = _channel_video()
    monkeypatch.setattr(
        handlers, "fetch_channel_videos", AsyncMock(return_value=[video])
    )
    subscription_id = _saved_subscription()
    callback = _callback(31, f"sec:{subscription_id}:videos")

    await handle_section_selected(callback)

    callback.answer.assert_awaited_once()
    assert _any_answer(callback.message, SECTION_LOADING_TEXT)
    assert _any_answer(callback.message, SECTION_LIST_TITLE_TEXT.format(title="NASA"))
    photo_kwargs = callback.message.answer_photo.await_args.kwargs
    assert photo_kwargs["photo"] == video.thumbnail_url
    assert photo_kwargs["reply_markup"].inline_keyboard[0][0].callback_data == (
        "dl:dQw4w9WgXcQ"
    )


async def test_handle_section_selected_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(handlers, "fetch_channel_videos", AsyncMock(return_value=[]))
    subscription_id = _saved_subscription()
    callback = _callback(31, f"sec:{subscription_id}:shorts")

    await handle_section_selected(callback)

    assert _any_answer(callback.message, SECTION_EMPTY_TEXT)
    callback.message.answer_photo.assert_not_awaited()


async def test_handle_section_selected_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        handlers,
        "fetch_channel_videos",
        AsyncMock(side_effect=ExtractionError("boom")),
    )
    subscription_id = _saved_subscription()
    callback = _callback(31, f"sec:{subscription_id}:streams")

    await handle_section_selected(callback)

    assert _any_answer(callback.message, SECTION_FAILED_TEXT)


async def test_handle_section_selected_expired() -> None:
    callback = _callback(31, "sec:999:videos")

    await handle_section_selected(callback)

    callback.message.answer.assert_awaited_once_with(SECTION_EXPIRED_TEXT)


async def test_handle_section_selected_without_message() -> None:
    callback = _callback(31, "sec:1:videos")
    callback.message = None

    await handle_section_selected(callback)

    callback.answer.assert_awaited_once()


def _video_info() -> VideoInfo:
    return VideoInfo(
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        title="Rick Astley",
        duration=213,
        uploader="Rick",
        formats=[_video_format()],
        thumbnail="https://i.ytimg.com/vi/dQw4w9WgXcQ/mqdefault.jpg",
    )


async def test_handle_video_selected_shows_formats(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        handlers, "fetch_video_info", AsyncMock(return_value=_video_info())
    )
    callback = _callback(41, "dl:dQw4w9WgXcQ")

    await handle_video_selected(callback)

    callback.answer.assert_awaited_once_with(FORMATS_PREPARING_TEXT)
    photo_kwargs = callback.message.answer_photo.await_args.kwargs
    assert photo_kwargs["reply_markup"].inline_keyboard[0][0].callback_data == "fmt:137"
    assert handlers._last_video[41].title == "Rick Astley"


async def test_handle_video_selected_handles_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        handlers,
        "fetch_video_info",
        AsyncMock(side_effect=ExtractionError("boom")),
    )
    callback = _callback(41, "dl:abc")

    await handle_video_selected(callback)

    assert _any_answer(callback.message, EXTRACTION_FAILED_TEXT)


async def test_handle_video_selected_rate_limited(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fetch = AsyncMock(return_value=_video_info())
    monkeypatch.setattr(handlers, "fetch_video_info", fetch)
    handlers._rate_limiter.allow(41)
    callback = _callback(41, "dl:dQw4w9WgXcQ")

    await handle_video_selected(callback)

    callback.message.answer.assert_awaited_once_with(RATE_LIMITED_TEXT)
    fetch.assert_not_awaited()


async def test_handle_video_selected_empty_id() -> None:
    callback = _callback(41, "dl:")

    await handle_video_selected(callback)

    callback.message.answer.assert_awaited_once_with(SECTION_EXPIRED_TEXT)


async def test_handle_video_selected_without_message() -> None:
    callback = _callback(41, "dl:abc")
    callback.message = None

    await handle_video_selected(callback)

    callback.answer.assert_awaited_once()
