# SPDX-FileCopyrightText: Copyright (c) 2026 VasilevNStas
# SPDX-License-Identifier: MIT
"""Download a selected format to a local file via yt-dlp."""

import asyncio
from pathlib import Path
from typing import Any

import yt_dlp

MAX_FILE_SIZE = 50 * 1024 * 1024


class DownloadError(Exception):
    """Raised when downloading a selected format fails."""


def download_format(url: str, format_id: str, dest_dir: str | Path) -> Path:
    """Download a single ``format_id`` of ``url`` into ``dest_dir``."""
    options: dict[str, Any] = {
        "quiet": True,
        "format": format_id,
        "outtmpl": str(Path(dest_dir) / "%(id)s.%(ext)s"),
        "noplaylist": True,
    }
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
            if info is None:
                raise DownloadError(f"yt-dlp returned no data for {url}")
            path = ydl.prepare_filename(info)
    except yt_dlp.utils.DownloadError as exc:
        raise DownloadError(str(exc)) from exc
    return Path(path)


async def fetch_format(url: str, format_id: str, dest_dir: str | Path) -> Path:
    """Async wrapper around :func:`download_format` (runs in a worker thread)."""
    return await asyncio.to_thread(download_format, url, format_id, dest_dir)
