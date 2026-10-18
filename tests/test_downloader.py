# SPDX-FileCopyrightText: Copyright (c) 2026 VasilevNStas
# SPDX-License-Identifier: MIT
"""Tests for the yt-dlp download wrapper."""

from pathlib import Path
from typing import Any

import pytest

from tg_bot_ytdl import downloader
from tg_bot_ytdl.downloader import DownloadError, download_format


class _FakeYDL:
    def __init__(self, params: dict[str, Any]) -> None:
        self.params = params

    def __enter__(self) -> "_FakeYDL":
        return self

    def __exit__(self, *exc: object) -> bool:
        return False

    def extract_info(self, url: str, download: bool = False) -> dict[str, Any]:
        return {"id": "abc", "ext": "mp4"}

    def prepare_filename(self, info: dict[str, Any]) -> str:
        outtmpl = self.params["outtmpl"]
        return outtmpl.replace("%(id)s", info["id"]).replace("%(ext)s", info["ext"])


def test_download_format_returns_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(downloader.yt_dlp, "YoutubeDL", _FakeYDL)

    path = download_format("https://youtu.be/x", "137", tmp_path)

    assert path == tmp_path / "abc.mp4"


def test_download_format_passes_format_id(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured: dict[str, Any] = {}

    class _CapturingYDL(_FakeYDL):
        def __init__(self, params: dict[str, Any]) -> None:
            super().__init__(params)
            captured.update(params)

    monkeypatch.setattr(downloader.yt_dlp, "YoutubeDL", _CapturingYDL)

    download_format("https://youtu.be/x", "137", tmp_path)

    assert captured["format"] == "137"
    assert captured["noplaylist"] is True


class _FailingYDL(_FakeYDL):
    def extract_info(self, url: str, download: bool = False) -> dict[str, Any]:
        raise downloader.yt_dlp.utils.DownloadError("boom")


def test_download_format_wraps_download_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(downloader.yt_dlp, "YoutubeDL", _FailingYDL)

    with pytest.raises(DownloadError):
        download_format("https://youtu.be/x", "137", tmp_path)


async def test_fetch_format_times_out(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import time

    def _slow(*args: object, **kwargs: object) -> Path:
        time.sleep(0.5)
        return tmp_path / "abc.mp4"

    monkeypatch.setattr(downloader, "download_format", _slow)
    monkeypatch.setattr(downloader, "DOWNLOAD_TIMEOUT", 0.01)

    with pytest.raises(DownloadError):
        await downloader.fetch_format("https://youtu.be/x", "137", tmp_path)
