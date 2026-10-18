# SPDX-FileCopyrightText: Copyright (c) 2026 VasilevNStas
# SPDX-License-Identifier: MIT
"""Tests for the database engine and metadata."""

from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session

from tg_bot_ytdl import db, models  # noqa: F401


def test_create_db_engine_creates_tables(tmp_path: Path) -> None:
    engine = db.create_db_engine(f"sqlite:///{tmp_path / 'test.db'}")
    try:
        db.Base.metadata.create_all(engine)
        tables = set(inspect(engine).get_table_names())
        assert {"users", "download_requests"} <= tables
    finally:
        engine.dispose()


def test_create_session_factory_returns_session(tmp_path: Path) -> None:
    engine = db.create_db_engine(f"sqlite:///{tmp_path / 'session.db'}")
    try:
        factory = db.create_session_factory(engine)
        with factory() as session:
            assert isinstance(session, Session)
    finally:
        engine.dispose()


def test_get_engine_creates_lazily(monkeypatch: pytest.MonkeyPatch) -> None:
    sentinel = object()
    monkeypatch.setattr(db, "_engine", None)
    monkeypatch.setattr(db, "create_db_engine", lambda: sentinel)

    assert db.get_engine() is sentinel


def test_get_session_factory_creates_lazily(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine("sqlite://", future=True)
    monkeypatch.setattr(db, "_session_factory", None)
    monkeypatch.setattr(db, "_engine", engine)

    factory = db.get_session_factory()

    assert factory is db._session_factory
    engine.dispose()


def test_session_scope_rolls_back_on_error() -> None:
    with pytest.raises(ValueError):
        with db.session_scope() as session:
            session.add(models.User(telegram_id=999, username="temp"))
            session.flush()
            raise ValueError("boom")

    with db.session_scope() as session:
        assert (
            session.scalar(select(models.User).where(models.User.telegram_id == 999))
            is None
        )


def test_init_db_creates_tables() -> None:
    db.init_db()

    tables = set(inspect(db.get_engine()).get_table_names())
    assert {"users", "download_requests"} <= tables
