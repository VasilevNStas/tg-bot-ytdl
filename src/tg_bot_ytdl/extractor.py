# SPDX-FileCopyrightText: Copyright (c) 2026 VasilevNStas
# SPDX-License-Identifier: MIT
"""YouTube URL validation and yt-dlp metadata extraction."""

import asyncio
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import yt_dlp

_ALLOWED_HOSTS = frozenset(
    {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "music.youtube.com",
        "youtu.be",
    }
)


class ExtractionError(Exception):
    """Raised when metadata extraction fails."""


@dataclass(frozen=True)
class VideoFormat:
    """A single downloadable format reported by yt-dlp."""

    format_id: str
    ext: str
    resolution: str | None
    filesize: int | None
    note: str | None


@dataclass(frozen=True)
class VideoInfo:
    """Metadata for a YouTube video."""

    url: str
    title: str
    duration: int | None
    uploader: str | None
    formats: list[VideoFormat]


def is_supported_url(url: str) -> bool:
    """Return ``True`` if ``url`` points to a supported YouTube host."""
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https"):
        return False
    return parsed.hostname in _ALLOWED_HOSTS


def _build_format(raw: dict[str, Any]) -> VideoFormat:
    return VideoFormat(
        format_id=str(raw.get("format_id", "")),
        ext=str(raw.get("ext", "")),
        resolution=raw.get("resolution") or raw.get("format_note"),
        filesize=raw.get("filesize") or raw.get("filesize_approx"),
        note=raw.get("format_note"),
    )


def _build_info(raw: dict[str, Any], url: str) -> VideoInfo:
    return VideoInfo(
        url=raw.get("webpage_url") or url,
        title=str(raw.get("title", "")),
        duration=raw.get("duration"),
        uploader=raw.get("uploader"),
        formats=[_build_format(f) for f in raw.get("formats") or []],
    )


def extract_info(url: str) -> VideoInfo:
    """Extract metadata for ``url`` synchronously via yt-dlp."""
    options: dict[str, Any] = {"quiet": True, "skip_download": True}
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            raw = ydl.extract_info(url, download=False)
    except yt_dlp.utils.DownloadError as exc:
        raise ExtractionError(str(exc)) from exc
    if raw is None:
        raise ExtractionError(f"yt-dlp returned no metadata for {url}")
    return _build_info(raw, url)


async def fetch_video_info(url: str) -> VideoInfo:
    """Async wrapper around :func:`extract_info` (runs in a worker thread)."""
    return await asyncio.to_thread(extract_info, url)
