# SPDX-FileCopyrightText: Copyright (c) 2026 VasilevNStas
# SPDX-License-Identifier: MIT
"""Persistence helpers for users and download history."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from tg_bot_ytdl.extractor import VideoFormat, VideoInfo
from tg_bot_ytdl.models import DownloadRequest, User

STATUS_SENT = "sent"
STATUS_TOO_LARGE = "too_large"
STATUS_FAILED = "failed"


def _utcnow() -> datetime:
    """Return the current timezone-aware UTC timestamp."""
    return datetime.now(UTC)


def get_or_create_user(
    session: Session,
    telegram_id: int,
    username: str | None = None,
) -> User:
    """Return the user for ``telegram_id``, creating it on first sight."""
    user = session.scalar(select(User).where(User.telegram_id == telegram_id))
    if user is None:
        user = User(telegram_id=telegram_id, username=username)
        session.add(user)
        session.flush()
        return user
    user.last_seen = _utcnow()
    if username is not None:
        user.username = username
    return user


def record_download(
    session: Session,
    telegram_id: int,
    username: str | None,
    *,
    info: VideoInfo,
    fmt: VideoFormat,
    status: str,
) -> DownloadRequest:
    """Persist a download attempt for ``telegram_id``."""
    user = get_or_create_user(session, telegram_id, username)
    request = DownloadRequest(
        user_id=user.id,
        url=info.url,
        title=info.title or None,
        format_id=fmt.format_id,
        ext=fmt.ext,
        resolution=fmt.resolution,
        filesize=fmt.filesize,
        status=status,
    )
    session.add(request)
    session.flush()
    return request
