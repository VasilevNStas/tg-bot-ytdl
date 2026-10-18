# SPDX-FileCopyrightText: Copyright (c) 2026 VasilevNStas
# SPDX-License-Identifier: MIT
"""Tests for application configuration."""

import pytest

from tg_bot_ytdl.config import Settings, get_settings


def test_settings_reads_bot_token_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BOT_TOKEN", "123:test-token")
    settings = Settings()
    assert settings.bot_token == "123:test-token"


def test_settings_defaults_to_empty_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    settings = Settings()
    assert settings.bot_token == ""


def test_get_settings_returns_settings() -> None:
    assert isinstance(get_settings(), Settings)
