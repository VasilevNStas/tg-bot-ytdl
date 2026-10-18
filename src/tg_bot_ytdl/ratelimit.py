# SPDX-FileCopyrightText: Copyright (c) 2026 VasilevNStas
# SPDX-License-Identifier: MIT
"""In-memory per-user rate limiting."""

import time

RATE_LIMIT_SECONDS = 3.0


class RateLimiter:
    """Allow at most one action per user within a rolling time window."""

    def __init__(self, interval: float = RATE_LIMIT_SECONDS) -> None:
        self._interval = interval
        self._last: dict[int, float] = {}

    def allow(self, user_id: int, *, now: float | None = None) -> bool:
        """Return ``True`` if ``user_id`` may act now, updating its timestamp."""
        current = time.monotonic() if now is None else now
        last = self._last.get(user_id)
        if last is not None and current - last < self._interval:
            return False
        self._last[user_id] = current
        return True

    def reset(self) -> None:
        """Forget all recorded timestamps."""
        self._last.clear()
