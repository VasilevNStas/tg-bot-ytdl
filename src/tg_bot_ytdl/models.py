# SPDX-FileCopyrightText: Copyright (c) 2026 VasilevNStas
# SPDX-License-Identifier: MIT
"""ORM models for users and download history."""

from datetime import UTC, datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tg_bot_ytdl.db import Base


def _utcnow() -> datetime:
    """Return the current timezone-aware UTC timestamp."""
    return datetime.now(UTC)


class User(Base):
    """A Telegram user known to the bot."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64), default=None)
    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    downloads: Mapped[list["DownloadRequest"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class DownloadRequest(Base):
    """A single chosen format that the bot attempted to download."""

    __tablename__ = "download_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    url: Mapped[str] = mapped_column(String(2048))
    title: Mapped[str | None] = mapped_column(String(512), default=None)
    format_id: Mapped[str] = mapped_column(String(64))
    ext: Mapped[str] = mapped_column(String(16))
    resolution: Mapped[str | None] = mapped_column(String(32), default=None)
    filesize: Mapped[int | None] = mapped_column(default=None)
    status: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    user: Mapped[User] = relationship(back_populates="downloads")
