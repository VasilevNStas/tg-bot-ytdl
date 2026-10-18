# SPDX-FileCopyrightText: Copyright (c) 2026 VasilevNStas
# SPDX-License-Identifier: MIT
"""Application configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables and ``.env``."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str = ""


def get_settings() -> Settings:
    """Build a fresh ``Settings`` instance."""
    return Settings()
