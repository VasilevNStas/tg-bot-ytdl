# SPDX-FileCopyrightText: Copyright (c) 2026 VasilevNStas
# SPDX-License-Identifier: MIT
"""Tests for the in-memory rate limiter."""

from tg_bot_ytdl.ratelimit import RateLimiter


def test_allows_first_action() -> None:
    limiter = RateLimiter(interval=3.0)
    assert limiter.allow(1, now=100.0)


def test_blocks_action_within_interval() -> None:
    limiter = RateLimiter(interval=3.0)
    assert limiter.allow(1, now=100.0)
    assert not limiter.allow(1, now=101.0)


def test_allows_action_after_interval() -> None:
    limiter = RateLimiter(interval=3.0)
    assert limiter.allow(1, now=100.0)
    assert limiter.allow(1, now=103.0)


def test_limits_are_per_user() -> None:
    limiter = RateLimiter(interval=3.0)
    assert limiter.allow(1, now=100.0)
    assert limiter.allow(2, now=100.0)


def test_reset_clears_state() -> None:
    limiter = RateLimiter(interval=3.0)
    assert limiter.allow(1, now=100.0)
    limiter.reset()
    assert limiter.allow(1, now=100.5)
