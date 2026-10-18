# SPDX-FileCopyrightText: Copyright (c) 2026 VasilevNStas
# SPDX-License-Identifier: MIT
"""Tests for the bot wiring and process entry point."""

import runpy
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest

from tg_bot_ytdl import main


class _FakeDispatcher:
    def __init__(self) -> None:
        self.routers: list[object] = []
        self.polled = False

    def include_router(self, router: object) -> None:
        self.routers.append(router)

    async def start_polling(self, bot: object) -> None:
        self.polled = True


def _patch(monkeypatch: pytest.MonkeyPatch) -> tuple[list[Any], _FakeDispatcher]:
    created: list[Any] = []

    class _FakeBot:
        def __init__(self, token: str) -> None:
            self.token = token
            self.session = SimpleNamespace(close=AsyncMock())
            created.append(self)

    dispatcher = _FakeDispatcher()
    monkeypatch.setattr(main, "Bot", _FakeBot)
    monkeypatch.setattr(main, "Dispatcher", lambda: dispatcher)
    monkeypatch.setattr(main, "init_db", lambda: None)
    monkeypatch.setattr(
        main,
        "get_settings",
        lambda: SimpleNamespace(require_bot_token=lambda: "token"),
    )
    return created, dispatcher


async def test_main_starts_polling(monkeypatch: pytest.MonkeyPatch) -> None:
    created, dispatcher = _patch(monkeypatch)

    await main.main()

    assert len(created) == 1
    assert created[0].token == "token"
    assert dispatcher.polled is True
    assert dispatcher.routers
    created[0].session.close.assert_awaited_once()


async def test_main_closes_session_on_error(monkeypatch: pytest.MonkeyPatch) -> None:
    created, dispatcher = _patch(monkeypatch)

    async def _boom(bot: object) -> None:
        raise RuntimeError("poll failed")

    monkeypatch.setattr(dispatcher, "start_polling", _boom)

    with pytest.raises(RuntimeError):
        await main.main()

    created[0].session.close.assert_awaited_once()


def test_run_delegates_to_asyncio(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[object] = []

    async def _fake_main() -> None:
        return None

    monkeypatch.setattr(main, "main", _fake_main)
    monkeypatch.setattr(main.logging, "basicConfig", lambda **kwargs: None)

    def _fake_run(coro: Any) -> None:
        seen.append(coro)
        coro.close()

    monkeypatch.setattr(main.asyncio, "run", _fake_run)

    main.run()

    assert len(seen) == 1


def test_module_entrypoint_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[bool] = []
    monkeypatch.setattr(main, "run", lambda: called.append(True))

    runpy.run_module("tg_bot_ytdl", run_name="__main__")

    assert called == [True]
