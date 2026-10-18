# SPDX-FileCopyrightText: Copyright (c) 2026 VasilevNStas
# SPDX-License-Identifier: MIT
"""Tests for URL validation and yt-dlp metadata extraction."""

import pytest

from tg_bot_ytdl import extractor
from tg_bot_ytdl.extractor import ExtractionError, extract_info, is_supported_url


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtube.com/watch?v=dQw4w9WgXcQ",
        "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://music.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
    ],
)
def test_is_supported_url_true(url: str) -> None:
    assert is_supported_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "",
        "not a url",
        "https://vimeo.com/12345",
        "ftp://youtube.com/watch?v=x",
        "https://evil-youtube.com/watch?v=x",
    ],
)
def test_is_supported_url_false(url: str) -> None:
    assert not is_supported_url(url)


class _FakeYDL:
    def __init__(self, options: dict[str, object]) -> None:
        self.options = options

    def __enter__(self) -> "_FakeYDL":
        return self

    def __exit__(self, *args: object) -> bool:
        return False

    def extract_info(self, url: str, download: bool = False) -> dict[str, object]:
        return {
            "webpage_url": url,
            "title": "Test Video",
            "duration": 125,
            "uploader": "Test Channel",
            "thumbnail": "https://i.ytimg.com/vi/x/hqdefault.jpg",
            "formats": [
                {
                    "format_id": "18",
                    "ext": "mp4",
                    "resolution": "360p",
                    "filesize": 1024,
                    "height": 360,
                    "vcodec": "avc1.42001E",
                    "acodec": "mp4a.40.2",
                }
            ],
        }


def test_extract_info_builds_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(extractor.yt_dlp, "YoutubeDL", _FakeYDL)

    info = extract_info("https://youtu.be/dQw4w9WgXcQ")

    assert info.title == "Test Video"
    assert info.uploader == "Test Channel"
    assert info.duration == 125
    assert len(info.formats) == 1
    assert info.formats[0].format_id == "18"
    assert info.formats[0].filesize == 1024
    assert info.formats[0].height == 360
    assert info.formats[0].has_video is True
    assert info.formats[0].has_audio is True
    assert info.thumbnail == "https://i.ytimg.com/vi/x/hqdefault.jpg"


class _FailingYDL(_FakeYDL):
    def extract_info(self, url: str, download: bool = False) -> dict[str, object]:
        raise extractor.yt_dlp.utils.DownloadError("boom")


def test_extract_info_wraps_download_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(extractor.yt_dlp, "YoutubeDL", _FailingYDL)

    with pytest.raises(ExtractionError):
        extract_info("https://youtu.be/dQw4w9WgXcQ")


class _EmptyYDL:
    def __init__(self, options: dict[str, object]) -> None:
        self.options = options

    def __enter__(self) -> "_EmptyYDL":
        return self

    def __exit__(self, *args: object) -> bool:
        return False

    def extract_info(self, url: str, download: bool = False) -> None:
        return None


def test_extract_info_raises_when_no_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(extractor.yt_dlp, "YoutubeDL", _EmptyYDL)

    with pytest.raises(ExtractionError):
        extract_info("https://youtu.be/dQw4w9WgXcQ")


async def test_fetch_video_info_times_out(monkeypatch: pytest.MonkeyPatch) -> None:
    import time

    def _slow(_url: str) -> object:
        time.sleep(0.5)
        return object()

    monkeypatch.setattr(extractor, "extract_info", _slow)
    monkeypatch.setattr(extractor, "EXTRACTION_TIMEOUT", 0.01)

    with pytest.raises(ExtractionError):
        await extractor.fetch_video_info("https://youtu.be/dQw4w9WgXcQ")
