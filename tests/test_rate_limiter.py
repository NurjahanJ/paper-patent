import asyncio
import time

from app.services.rate_limiter import TokenBucketRateLimiter


class TestTokenBucketRateLimiter:
    def test_immediate_acquire_within_capacity(self):
        """Tokens within capacity should be acquired instantly."""
        limiter = TokenBucketRateLimiter(capacity=1000, window_seconds=60.0)
        start = time.monotonic()
        asyncio.run(limiter.acquire(500))
        elapsed = time.monotonic() - start
        assert elapsed < 0.1  # Should be near-instant

    def test_waits_when_exhausted(self):
        """When tokens are exhausted, acquire should wait for refill."""
        # 100 tokens per second = tiny bucket that empties fast
        limiter = TokenBucketRateLimiter(capacity=100, window_seconds=1.0)

        async def drain_and_wait():
            await limiter.acquire(100)  # Drain the bucket
            start = time.monotonic()
            await limiter.acquire(50)   # Should wait ~0.5s for 50 tokens to refill
            elapsed = time.monotonic() - start
            return elapsed

        elapsed = asyncio.run(drain_and_wait())
        assert 0.3 < elapsed < 1.0  # Should wait roughly 0.5s

    def test_refills_over_time(self):
        """Tokens should refill after waiting."""
        limiter = TokenBucketRateLimiter(capacity=600, window_seconds=1.0)

        async def test():
            await limiter.acquire(600)  # Drain
            await asyncio.sleep(1.0)    # Wait for full refill
            start = time.monotonic()
            await limiter.acquire(300)  # Should be available now
            elapsed = time.monotonic() - start
            return elapsed

        elapsed = asyncio.run(test())
        assert elapsed < 0.1  # Should be near-instant after refill

    def test_concurrent_acquires_are_serialized(self):
        """Multiple concurrent acquires should not exceed capacity."""
        # 600 tokens/sec capacity, 10 acquires of 100 tokens each
        limiter = TokenBucketRateLimiter(capacity=600, window_seconds=1.0)

        async def test():
            start = time.monotonic()
            # Fire 10 acquires of 100 tokens = 1000 total, but capacity is only 600
            # So some should wait
            await asyncio.gather(*[limiter.acquire(100) for _ in range(10)])
            elapsed = time.monotonic() - start
            return elapsed

        elapsed = asyncio.run(test())
        # 1000 tokens needed, 600 available, 400 must wait for refill
        # At 600/sec refill rate, ~0.67s wait
        assert elapsed > 0.3  # Must have waited for some refill

    def test_matches_openai_scenario(self):
        """Simulate OpenAI's 30K TPM with 600 tokens per call."""
        limiter = TokenBucketRateLimiter(capacity=27_000, window_seconds=60.0)

        async def test():
            # First 45 calls should fit in budget (45 * 600 = 27,000)
            start = time.monotonic()
            for _ in range(45):
                await limiter.acquire(600)
            first_batch = time.monotonic() - start

            # 46th call should need to wait for refill
            wait_start = time.monotonic()
            await limiter.acquire(600)
            wait_time = time.monotonic() - wait_start

            return first_batch, wait_time

        first_batch, wait_time = asyncio.run(test())
        assert first_batch < 1.0  # First 45 should be fast
        assert wait_time > 0.5    # 46th should wait for token refill
