# SPDX-FileCopyrightText: Copyright (c) 2026 VasilevNStas
# SPDX-License-Identifier: MIT
"""Bot command list and menu button configuration."""

from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeDefault, MenuButtonCommands

BOT_COMMANDS = [
    BotCommand(command="start", description="Открыть меню"),
    BotCommand(command="subscriptions", description="Мои подписки"),
    BotCommand(command="help", description="Справка"),
]


async def configure_bot_ui(bot: Bot) -> None:
    """Register the command list and enable the menu button."""
    await bot.set_my_commands(BOT_COMMANDS, scope=BotCommandScopeDefault())
    await bot.set_chat_menu_button(menu_button=MenuButtonCommands())
