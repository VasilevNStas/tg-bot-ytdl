# SPDX-FileCopyrightText: Copyright (c) 2026 VasilevNStas
# SPDX-License-Identifier: MIT
"""Tests for the persistence helpers."""

from sqlalchemy import select

from tg_bot_ytdl import db
from tg_bot_ytdl.extractor import VideoFormat, VideoInfo
from tg_bot_ytdl.models import DownloadRequest, Subscription, User
from tg_bot_ytdl.repository import (
    STATUS_SENT,
    add_subscription,
    get_or_create_user,
    get_subscription,
    list_subscriptions,
    record_download,
    remove_subscription,
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


def test_add_subscription_creates_once() -> None:
    with db.session_scope() as session:
        subscription, created = add_subscription(
            session,
            5,
            "alice",
            channel_id="UC1",
            url="https://www.youtube.com/@nasa",
            title="NASA",
        )
        assert created is True
        assert subscription.title == "NASA"

    with db.session_scope() as session:
        again, created = add_subscription(
            session,
            5,
            "alice",
            channel_id="UC1",
            url="https://www.youtube.com/@nasa",
            title="NASA",
        )
        assert created is False
        assert again.channel_id == "UC1"

    with db.session_scope() as session:
        assert len(session.scalars(select(Subscription)).all()) == 1


def test_list_subscriptions_is_scoped_per_user() -> None:
    with db.session_scope() as session:
        add_subscription(session, 1, None, channel_id="UC1", url="u1", title="First")
        add_subscription(session, 1, None, channel_id="UC2", url="u2", title="Second")
        add_subscription(session, 2, None, channel_id="UC3", url="u3", title="Other")

    with db.session_scope() as session:
        titles = [sub.title for sub in list_subscriptions(session, 1)]
    assert titles == ["First", "Second"]

    with db.session_scope() as session:
        assert list_subscriptions(session, 999) == []


def test_get_and_remove_subscription() -> None:
    with db.session_scope() as session:
        subscription, _ = add_subscription(
            session, 4, None, channel_id="UC1", url="u1", title="Chan"
        )
        sub_id = subscription.id

    with db.session_scope() as session:
        assert get_subscription(session, 4, sub_id) is not None
        assert get_subscription(session, 4, sub_id + 100) is None
        assert get_subscription(session, 999, sub_id) is None

    with db.session_scope() as session:
        assert remove_subscription(session, 4, sub_id) is True
        assert remove_subscription(session, 4, sub_id) is False

    with db.session_scope() as session:
        assert session.scalar(select(Subscription)) is None
