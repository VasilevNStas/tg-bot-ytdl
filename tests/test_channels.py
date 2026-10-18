# SPDX-FileCopyrightText: Copyright (c) 2026 VasilevNStas
# SPDX-License-Identifier: MIT
"""Tests for channel detection and metadata lookup."""

import time
from typing import Any

import pytest

from tg_bot_ytdl import channels
from tg_bot_ytdl.channels import (
    ChannelInfo,
    ChannelVideo,
    extract_channel_info,
    extract_channel_videos,
    fetch_channel_info,
    fetch_channel_videos,
    is_channel_url,
    normalize_channel_url,
    section_url,
)
from tg_bot_ytdl.extractor import ExtractionError


class _FakeYDL:
    def __init__(self, params: dict[str, Any]) -> None:
        self.params = params

    def __enter__(self) -> "_FakeYDL":
        return self

    def __exit__(self, *args: object) -> bool:
        return False

    def extract_info(self, url: str, download: bool = False) -> dict[str, Any]:
        return {"id": "UC123", "title": "NASA", "webpage_url": url}


class _FailingYDL(_FakeYDL):
    def extract_info(self, url: str, download: bool = False) -> dict[str, Any]:
        raise channels.yt_dlp.utils.DownloadError("boom")


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/@NASA",
        "https://www.youtube.com/@NASA/videos",
        "https://youtube.com/channel/UCabc123",
        "https://www.youtube.com/c/NASA",
        "https://m.youtube.com/user/NASA",
    ],
)
def test_is_channel_url_true(url: str) -> None:
    assert is_channel_url(url) is True


@pytest.mark.parametrize(
    "url",
    [
        "",
        "not a url",
        "https://www.youtube.com/watch?v=abc",
        "https://www.youtube.com/shorts/abc",
        "https://youtu.be/abc",
        "https://music.youtube.com/@NASA",
        "https://vimeo.com/@NASA",
        "https://www.youtube.com/",
    ],
)
def test_is_channel_url_false(url: str) -> None:
    assert is_channel_url(url) is False


def test_normalize_channel_url_strips_tabs_and_query() -> None:
    assert (
        normalize_channel_url("https://www.youtube.com/@NASA/videos?si=x")
        == "https://www.youtube.com/@NASA"
    )
    assert (
        normalize_channel_url("https://youtube.com/channel/UCabc123/")
        == "https://youtube.com/channel/UCabc123"
    )


def test_extract_channel_info_builds_channel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(channels.yt_dlp, "YoutubeDL", _FakeYDL)

    info = extract_channel_info("https://www.youtube.com/@NASA")

    assert isinstance(info, ChannelInfo)
    assert info.channel_id == "UC123"
    assert info.title == "NASA"
    assert info.url == "https://www.youtube.com/@NASA"


def test_extract_channel_info_wraps_download_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(channels.yt_dlp, "YoutubeDL", _FailingYDL)

    with pytest.raises(ExtractionError):
        extract_channel_info("https://www.youtube.com/@NASA")


async def test_fetch_channel_info_times_out(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _slow(_url: str) -> ChannelInfo:
        time.sleep(0.5)
        raise AssertionError("should have timed out")

    monkeypatch.setattr(channels, "extract_channel_info", _slow)
    monkeypatch.setattr(channels, "EXTRACTION_TIMEOUT", 0.01)

    with pytest.raises(ExtractionError):
        await fetch_channel_info("https://www.youtube.com/@NASA")


class _VideosYDL(_FakeYDL):
    def extract_info(self, url: str, download: bool = False) -> dict[str, Any]:
        return {
            "entries": [
                {"id": "aaa", "title": "First", "duration": 75},
                {"id": "bbb", "title": "  Second   video ", "duration": None},
                "not a dict",
                {"id": "", "title": "skip"},
            ]
        }


class _EmptyYDL(_FakeYDL):
    def extract_info(self, url: str, download: bool = False) -> Any:
        return None


def test_section_url_appends_section() -> None:
    assert section_url("https://www.youtube.com/@NASA", "shorts") == (
        "https://www.youtube.com/@NASA/shorts"
    )


def test_section_url_strips_existing_tab() -> None:
    assert section_url("https://www.youtube.com/@NASA/videos", "streams") == (
        "https://www.youtube.com/@NASA/streams"
    )


def test_channel_video_thumbnail_url() -> None:
    video = ChannelVideo(video_id="abc", title="T", url="u")

    assert video.thumbnail_url == "https://i.ytimg.com/vi/abc/mqdefault.jpg"


def test_extract_channel_videos_builds_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(channels.yt_dlp, "YoutubeDL", _VideosYDL)

    videos = extract_channel_videos("https://www.youtube.com/@NASA/videos")

    assert [video.video_id for video in videos] == ["aaa", "bbb"]
    assert videos[0].url == "https://www.youtube.com/watch?v=aaa"
    assert videos[0].duration == 75
    assert videos[1].duration is None


def test_extract_channel_videos_respects_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(channels.yt_dlp, "YoutubeDL", _VideosYDL)

    videos = extract_channel_videos("https://www.youtube.com/@NASA/videos", limit=1)

    assert len(videos) == 1


def test_extract_channel_videos_raises_when_no_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(channels.yt_dlp, "YoutubeDL", _EmptyYDL)

    with pytest.raises(ExtractionError):
        extract_channel_videos("https://www.youtube.com/@NASA/videos")


def test_extract_channel_videos_wraps_download_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(channels.yt_dlp, "YoutubeDL", _FailingYDL)

    with pytest.raises(ExtractionError):
        extract_channel_videos("https://www.youtube.com/@NASA/videos")


async def test_fetch_channel_videos_times_out(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _slow(_url: str, _limit: int = 5) -> list[ChannelVideo]:
        time.sleep(0.5)
        raise AssertionError("should have timed out")

    monkeypatch.setattr(channels, "extract_channel_videos", _slow)
    monkeypatch.setattr(channels, "EXTRACTION_TIMEOUT", 0.01)

    with pytest.raises(ExtractionError):
        await fetch_channel_videos("https://www.youtube.com/@NASA/videos")
