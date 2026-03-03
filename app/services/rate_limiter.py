"""
Token-bucket rate limiter for API calls.

Enforces tokens-per-minute (TPM) limits by tracking token consumption
and sleeping when the budget is exhausted.
"""
import asyncio
import logging
import time

logger = logging.getLogger(__name__)


class TokenBucketRateLimiter:
    """
    Async rate limiter using a token-bucket algorithm.

    - capacity: max tokens available per window
    - window_seconds: how long the window is (default 60s = per minute)
    - Tokens refill continuously based on elapsed time.
    """

    def __init__(self, capacity: int, window_seconds: float = 60.0):
        self._capacity = capacity
        self._tokens = float(capacity)
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()
        self._refill_rate = capacity / window_seconds  # tokens per second

    async def acquire(self, tokens: int):
        """Wait until `tokens` budget is available, then consume them."""
        while True:
            async with self._lock:
                self._refill()

                if tokens <= self._tokens:
                    self._tokens -= tokens
                    return

                # Calculate wait time and reserve our spot by NOT refilling
                deficit = tokens - self._tokens
                wait_time = deficit / self._refill_rate

            logger.debug("Rate limiter: waiting %.1fs for %d tokens", wait_time, tokens)
            await asyncio.sleep(wait_time)

    def _refill(self):
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self._capacity, self._tokens + elapsed * self._refill_rate)
        self._last_refill = now
