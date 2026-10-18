# SPDX-FileCopyrightText: Copyright (c) 2026 VasilevNStas
# SPDX-License-Identifier: MIT
"""Tests for channel detection and metadata lookup."""

import time
from typing import Any

import pytest

from tg_bot_ytdl import channels
from tg_bot_ytdl.channels import (
    ChannelInfo,
    extract_channel_info,
    fetch_channel_info,
    is_channel_url,
    normalize_channel_url,
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
