# SPDX-FileCopyrightText: Copyright (c) 2026 VasilevNStas
# SPDX-License-Identifier: MIT
"""Tests for the bot command list and menu button."""

from unittest.mock import AsyncMock

from aiogram.types import BotCommandScopeDefault, MenuButtonCommands

from tg_bot_ytdl.commands import BOT_COMMANDS, configure_bot_ui


def test_bot_commands_cover_menu() -> None:
    commands = {command.command: command.description for command in BOT_COMMANDS}

    assert commands["start"] == "Открыть меню"
    assert commands["subscriptions"] == "Мои подписки"
    assert commands["help"] == "Справка"


async def test_configure_bot_ui_registers_commands_and_menu() -> None:
    bot = AsyncMock()

    await configure_bot_ui(bot)

    bot.set_my_commands.assert_awaited_once()
    commands = bot.set_my_commands.await_args.args[0]
    assert [command.command for command in commands] == [
        "start",
        "subscriptions",
        "help",
    ]
    assert isinstance(
        bot.set_my_commands.await_args.kwargs["scope"], BotCommandScopeDefault
    )

    bot.set_chat_menu_button.assert_awaited_once()
    menu_button = bot.set_chat_menu_button.await_args.kwargs["menu_button"]
    assert isinstance(menu_button, MenuButtonCommands)
