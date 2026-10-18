# SPDX-FileCopyrightText: Copyright (c) 2026 VasilevNStas
# SPDX-License-Identifier: MIT
"""Application configuration."""

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables and ``.env``."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: SecretStr = SecretStr("")

    def require_bot_token(self) -> str:
        """Return the bot token or raise if it is not configured."""
        token = self.bot_token.get_secret_value().strip()
        if not token:
            raise RuntimeError(
                "BOT_TOKEN is not set. Copy .env.example to .env and fill it in."
            )
        return token


def get_settings() -> Settings:
    """Build a fresh ``Settings`` instance."""
    return Settings()
