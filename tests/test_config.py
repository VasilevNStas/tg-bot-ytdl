# SPDX-FileCopyrightText: Copyright (c) 2026 VasilevNStas
# SPDX-License-Identifier: MIT
"""Tests for application configuration."""

import pytest

from tg_bot_ytdl.config import Settings, get_settings


def test_settings_reads_bot_token_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BOT_TOKEN", "123:test-token")
    settings = Settings(_env_file=None)
    assert settings.bot_token.get_secret_value() == "123:test-token"


def test_settings_defaults_to_empty_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    settings = Settings(_env_file=None)
    assert settings.bot_token.get_secret_value() == ""


def test_require_bot_token_returns_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BOT_TOKEN", "123:test-token")
    assert Settings(_env_file=None).require_bot_token() == "123:test-token"


def test_require_bot_token_raises_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="BOT_TOKEN is not set"):
        Settings(_env_file=None).require_bot_token()


def test_token_is_not_exposed_in_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BOT_TOKEN", "super-secret")
    assert "super-secret" not in repr(Settings(_env_file=None))


def test_get_settings_returns_settings() -> None:
    assert isinstance(get_settings(), Settings)
