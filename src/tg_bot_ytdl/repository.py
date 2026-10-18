# SPDX-FileCopyrightText: Copyright (c) 2026 VasilevNStas
# SPDX-License-Identifier: MIT
"""Persistence helpers for users and download history."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from tg_bot_ytdl.extractor import VideoFormat, VideoInfo
from tg_bot_ytdl.models import DownloadRequest, Subscription, User

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


def add_subscription(
    session: Session,
    telegram_id: int,
    username: str | None,
    *,
    channel_id: str,
    url: str,
    title: str,
) -> tuple[Subscription, bool]:
    """Save a channel for ``telegram_id``; return it and whether it is new."""
    user = get_or_create_user(session, telegram_id, username)
    existing = session.scalar(
        select(Subscription).where(
            Subscription.user_id == user.id,
            Subscription.channel_id == channel_id,
        )
    )
    if existing is not None:
        return existing, False
    subscription = Subscription(
        user_id=user.id,
        channel_id=channel_id,
        url=url,
        title=title,
    )
    session.add(subscription)
    session.flush()
    return subscription, True


def list_subscriptions(session: Session, telegram_id: int) -> list[Subscription]:
    """Return the channels saved by ``telegram_id``, oldest first."""
    user = session.scalar(select(User).where(User.telegram_id == telegram_id))
    if user is None:
        return []
    return list(
        session.scalars(
            select(Subscription)
            .where(Subscription.user_id == user.id)
            .order_by(Subscription.added_at, Subscription.id)
        )
    )


def get_subscription(
    session: Session,
    telegram_id: int,
    subscription_id: int,
) -> Subscription | None:
    """Return one saved channel of ``telegram_id`` or ``None``."""
    user = session.scalar(select(User).where(User.telegram_id == telegram_id))
    if user is None:
        return None
    return session.scalar(
        select(Subscription).where(
            Subscription.id == subscription_id,
            Subscription.user_id == user.id,
        )
    )


def remove_subscription(
    session: Session,
    telegram_id: int,
    subscription_id: int,
) -> bool:
    """Delete one saved channel of ``telegram_id``; return whether it existed."""
    subscription = get_subscription(session, telegram_id, subscription_id)
    if subscription is None:
        return False
    session.delete(subscription)
    session.flush()
    return True
