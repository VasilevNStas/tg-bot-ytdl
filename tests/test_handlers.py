# SPDX-FileCopyrightText: Copyright (c) 2026 VasilevNStas
# SPDX-License-Identifier: MIT
"""Tests for command handlers."""

from unittest.mock import AsyncMock

from tg_bot_ytdl.handlers import HELP_TEXT, START_TEXT, handle_help, handle_start


async def test_handle_start_replies() -> None:
    message = AsyncMock()
    await handle_start(message)
    message.answer.assert_awaited_once_with(START_TEXT)


async def test_handle_help_replies() -> None:
    message = AsyncMock()
    await handle_help(message)
    message.answer.assert_awaited_once_with(HELP_TEXT)
