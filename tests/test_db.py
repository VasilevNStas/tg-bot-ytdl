# SPDX-FileCopyrightText: Copyright (c) 2026 VasilevNStas
# SPDX-License-Identifier: MIT
"""Tests for the database engine and metadata."""

from pathlib import Path

from sqlalchemy import inspect

from tg_bot_ytdl import db, models  # noqa: F401


def test_create_db_engine_creates_tables(tmp_path: Path) -> None:
    engine = db.create_db_engine(f"sqlite:///{tmp_path / 'test.db'}")
    try:
        db.Base.metadata.create_all(engine)
        tables = set(inspect(engine).get_table_names())
        assert {"users", "download_requests"} <= tables
    finally:
        engine.dispose()
