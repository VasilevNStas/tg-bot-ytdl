# SPDX-FileCopyrightText: Copyright (c) 2026 VasilevNStas
# SPDX-License-Identifier: MIT
"""Download a selected format to a local file via yt-dlp."""

import asyncio
from pathlib import Path
from typing import Any

import yt_dlp

MAX_FILE_SIZE = 50 * 1024 * 1024
DOWNLOAD_TIMEOUT = 120.0
MP3_QUALITY = "192"


class DownloadError(Exception):
    """Raised when downloading a selected format fails."""


def download_format(
    url: str,
    format_id: str,
    dest_dir: str | Path,
    *,
    merge_audio: bool = False,
    audio_only: bool = False,
) -> Path:
    """Download a single ``format_id`` of ``url`` into ``dest_dir``."""
    options: dict[str, Any] = {
        "quiet": True,
        "outtmpl": str(Path(dest_dir) / "%(id)s.%(ext)s"),
        "noplaylist": True,
    }
    if audio_only:
        options["format"] = "bestaudio/best"
        options["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": MP3_QUALITY,
            }
        ]
    else:
        options["format"] = (
            f"{format_id}+bestaudio/{format_id}" if merge_audio else format_id
        )
        if merge_audio:
            options["merge_output_format"] = "mp4"
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
            if info is None:
                raise DownloadError(f"yt-dlp returned no data for {url}")
            path = Path(_downloaded_path(ydl, info))
    except yt_dlp.utils.DownloadError as exc:
        raise DownloadError(str(exc)) from exc
    if audio_only:
        mp3_path = path.with_suffix(".mp3")
        if mp3_path.exists():
            path = mp3_path
    return path


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
    audio_only: bool = False,
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
                audio_only=audio_only,
            ),
            timeout=DOWNLOAD_TIMEOUT,
        )
    except TimeoutError as exc:
        raise DownloadError(str(exc)) from exc
