# SPDX-FileCopyrightText: Copyright (c) 2026 VasilevNStas
# SPDX-License-Identifier: MIT
"""Download a selected format to a local file via yt-dlp."""

import asyncio
from pathlib import Path
from typing import Any

import yt_dlp

MAX_FILE_SIZE = 50 * 1024 * 1024
DOWNLOAD_TIMEOUT = 120.0


class DownloadError(Exception):
    """Raised when downloading a selected format fails."""


def download_format(
    url: str,
    format_id: str,
    dest_dir: str | Path,
    *,
    merge_audio: bool = False,
) -> Path:
    """Download a single ``format_id`` of ``url`` into ``dest_dir``."""
    selector = f"{format_id}+bestaudio/{format_id}" if merge_audio else format_id
    options: dict[str, Any] = {
        "quiet": True,
        "format": selector,
        "outtmpl": str(Path(dest_dir) / "%(id)s.%(ext)s"),
        "noplaylist": True,
    }
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
            if info is None:
                raise DownloadError(f"yt-dlp returned no data for {url}")
            path = _downloaded_path(ydl, info)
    except yt_dlp.utils.DownloadError as exc:
        raise DownloadError(str(exc)) from exc
    return Path(path)


def _downloaded_path(ydl: Any, info: dict[str, Any]) -> str:
    requested = info.get("requested_downloads") or []
    if requested and requested[0].get("filepath"):
        return requested[0]["filepath"]
    return ydl.prepare_filename(info)


async def fetch_format(
    url: str,
    format_id: str,
    dest_dir: str | Path,
    *,
    merge_audio: bool = False,
) -> Path:
    """Async wrapper around :func:`download_format` (runs in a worker thread)."""
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(
                download_format,
                url,
                format_id,
                dest_dir,
                merge_audio=merge_audio,
            ),
            timeout=DOWNLOAD_TIMEOUT,
        )
    except TimeoutError as exc:
        raise DownloadError(str(exc)) from exc
