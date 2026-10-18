# SPDX-FileCopyrightText: Copyright (c) 2026 VasilevNStas
# SPDX-License-Identifier: MIT
"""Tests for the persistence helpers."""

from sqlalchemy import select

from tg_bot_ytdl import db
from tg_bot_ytdl.extractor import VideoFormat, VideoInfo
from tg_bot_ytdl.models import DownloadRequest, User
from tg_bot_ytdl.repository import (
    STATUS_SENT,
    get_or_create_user,
    record_download,
)


def _info() -> VideoInfo:
    return VideoInfo(
        url="https://youtu.be/x",
        title="Test Video",
        duration=65,
        uploader="Test Channel",
        formats=[],
    )


def _fmt() -> VideoFormat:
    return VideoFormat(
        format_id="137",
        ext="mp4",
        resolution="1280x720",
        filesize=1024,
        note=None,
    )


def test_get_or_create_user_creates_once() -> None:
    with db.session_scope() as session:
        user = get_or_create_user(session, 42, "alice")
        assert user.telegram_id == 42
        assert user.username == "alice"
        assert user.first_seen is not None

    with db.session_scope() as session:
        again = get_or_create_user(session, 42, "alice2")
        assert again.telegram_id == 42
        assert again.username == "alice2"

    with db.session_scope() as session:
        users = session.scalars(select(User)).all()
        assert len(users) == 1


def test_record_download_links_user_and_format() -> None:
    with db.session_scope() as session:
        record_download(
            session,
            7,
            "bob",
            info=_info(),
            fmt=_fmt(),
            status=STATUS_SENT,
        )

    with db.session_scope() as session:
        request = session.scalar(select(DownloadRequest))
        user = session.scalar(select(User).where(User.telegram_id == 7))
        assert request is not None
        assert user is not None
        assert request.user_id == user.id
        assert request.status == STATUS_SENT
        assert request.format_id == "137"
        assert request.title == "Test Video"
