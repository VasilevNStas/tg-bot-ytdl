# SPDX-FileCopyrightText: Copyright (c) 2026 VasilevNStas
# SPDX-License-Identifier: MIT
"""Package-level smoke tests."""

import tg_bot_ytdl


def test_package_version() -> None:
    assert tg_bot_ytdl.__version__ == "0.1.0"
