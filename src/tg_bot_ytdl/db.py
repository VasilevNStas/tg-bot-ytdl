# SPDX-FileCopyrightText: Copyright (c) 2026 VasilevNStas
# SPDX-License-Identifier: MIT
"""Database engine, session factory and declarative base."""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from tg_bot_ytdl.config import get_settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def create_db_engine(database_url: str | None = None) -> Engine:
    """Create a SQLAlchemy engine for the given (or configured) URL."""
    url = database_url or get_settings().database_url
    return create_engine(url, future=True)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Build a session factory bound to ``engine``."""
    return sessionmaker(bind=engine, expire_on_commit=False)


_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    """Return the lazily created process-wide engine."""
    global _engine
    if _engine is None:
        _engine = create_db_engine()
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """Return the lazily created process-wide session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = create_session_factory(get_engine())
    return _session_factory


@contextmanager
def session_scope() -> Iterator[Session]:
    """Open a session, commit on success and roll back on error."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """Create all tables for the current models."""
    from tg_bot_ytdl import models  # noqa: F401

    Base.metadata.create_all(get_engine())
