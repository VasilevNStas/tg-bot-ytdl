# SPDX-FileCopyrightText: Copyright (c) 2026 VasilevNStas
# SPDX-License-Identifier: MIT
"""Detection and metadata lookup for public YouTube channels."""

import asyncio
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import yt_dlp

from tg_bot_ytdl.extractor import EXTRACTION_TIMEOUT, ExtractionError

_CHANNEL_HOSTS = frozenset({"youtube.com", "www.youtube.com", "m.youtube.com"})

_CHANNEL_SEGMENTS = frozenset({"channel", "c", "user"})

_TAB_SUFFIXES = frozenset(
    {"videos", "shorts", "streams", "playlists", "featured", "about", "community"}
)

SECTION_VIDEOS = "videos"
SECTION_SHORTS = "shorts"
SECTION_STREAMS = "streams"

SECTIONS = (SECTION_VIDEOS, SECTION_SHORTS, SECTION_STREAMS)

VIDEO_LIST_LIMIT = 5


@dataclass(frozen=True)
class ChannelInfo:
    """A public YouTube channel."""

    channel_id: str
    url: str
    title: str


@dataclass(frozen=True)
class ChannelVideo:
    """A single video listed on a channel page."""

    video_id: str
    title: str
    url: str
    duration: int | None = None

    @property
    def thumbnail_url(self) -> str:
        """Return a public thumbnail URL for the video."""
        return f"https://i.ytimg.com/vi/{self.video_id}/mqdefault.jpg"


def _channel_path(url: str) -> str | None:
    """Return the channel path (without tab suffix) or ``None``."""
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https"):
        return None
    if parsed.hostname not in _CHANNEL_HOSTS:
        return None
    segments = [segment for segment in parsed.path.split("/") if segment]
    if not segments:
        return None
    head = segments[0]
    if not (head.startswith("@") or head in _CHANNEL_SEGMENTS):
        return None
    if len(segments) > 1 and segments[1] in _TAB_SUFFIXES:
        segments = segments[:1]
    return "/".join(segments)


def is_channel_url(url: str) -> bool:
    """Return ``True`` if ``url`` points to a public YouTube channel."""
    return _channel_path(url) is not None


def normalize_channel_url(url: str) -> str:
    """Return a canonical channel URL without tabs, query or fragment."""
    parsed = urlparse(url.strip())
    path = _channel_path(url)
    if path is None:
        return url.strip().rstrip("/")
    return f"{parsed.scheme}://{parsed.hostname}/{path}"


def _build_channel_info(raw: dict[str, Any], url: str) -> ChannelInfo:
    channel_id = str(raw.get("channel_id") or raw.get("id") or "").strip()
    if not channel_id:
        channel_id = normalize_channel_url(url)
    title = str(raw.get("title") or raw.get("channel") or "").strip() or channel_id
    page_url = str(raw.get("webpage_url") or raw.get("url") or url)
    return ChannelInfo(channel_id=channel_id, url=page_url, title=title)


def extract_channel_info(url: str) -> ChannelInfo:
    """Look up channel metadata synchronously via yt-dlp."""
    options: dict[str, Any] = {
        "quiet": True,
        "skip_download": True,
        "extract_flat": True,
        "playlistend": 1,
    }
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            raw = ydl.extract_info(url, download=False)
    except yt_dlp.utils.DownloadError as exc:
        raise ExtractionError(str(exc)) from exc
    if raw is None:
        raise ExtractionError(f"yt-dlp returned no channel info for {url}")
    return _build_channel_info(raw, url)


async def fetch_channel_info(url: str) -> ChannelInfo:
    """Async wrapper around :func:`extract_channel_info`."""
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(extract_channel_info, url),
            timeout=EXTRACTION_TIMEOUT,
        )
    except TimeoutError as exc:
        raise ExtractionError(str(exc)) from exc


def section_url(channel_url: str, section: str) -> str:
    """Build the URL of a channel tab (``videos``/``shorts``/``streams``)."""
    base = channel_url.strip().rstrip("/")
    for tab in _TAB_SUFFIXES:
        suffix = f"/{tab}"
        if base.endswith(suffix):
            base = base[: -len(suffix)].rstrip("/")
            break
    return f"{base}/{section}"


def _build_channel_videos(raw: dict[str, Any], limit: int) -> list[ChannelVideo]:
    videos: list[ChannelVideo] = []
    entries = raw.get("entries") or []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        video_id = str(entry.get("id") or "").strip()
        if not video_id:
            continue
        title = str(entry.get("title") or "").strip() or video_id
        duration = entry.get("duration")
        videos.append(
            ChannelVideo(
                video_id=video_id,
                title=title,
                url=f"https://www.youtube.com/watch?v={video_id}",
                duration=duration if isinstance(duration, int) else None,
            )
        )
        if len(videos) >= limit:
            break
    return videos


def extract_channel_videos(
    url: str,
    limit: int = VIDEO_LIST_LIMIT,
) -> list[ChannelVideo]:
    """List recent videos of a channel tab synchronously via yt-dlp."""
    options: dict[str, Any] = {
        "quiet": True,
        "skip_download": True,
        "extract_flat": True,
        "playlistend": limit,
    }
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            raw = ydl.extract_info(url, download=False)
    except yt_dlp.utils.DownloadError as exc:
        raise ExtractionError(str(exc)) from exc
    if raw is None:
        raise ExtractionError(f"yt-dlp returned no videos for {url}")
    return _build_channel_videos(raw, limit)


async def fetch_channel_videos(
    url: str,
    limit: int = VIDEO_LIST_LIMIT,
) -> list[ChannelVideo]:
    """Async wrapper around :func:`extract_channel_videos`."""
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(extract_channel_videos, url, limit),
            timeout=EXTRACTION_TIMEOUT,
        )
    except TimeoutError as exc:
        raise ExtractionError(str(exc)) from exc
