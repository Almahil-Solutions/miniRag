import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException
from utils.rate_limiter import RateLimiter, rate_limit_dependency, PLAN_LIMITS


class TestRateLimiterUnit:
    @pytest.fixture
    def mock_redis(self):
        redis = AsyncMock()
        redis.incr = AsyncMock(return_value=1)
        redis.expire = AsyncMock(return_value=True)
        redis.ttl = AsyncMock(return_value=45)
        return redis

    @pytest.mark.asyncio
    async def test_allows_within_quota(self, mock_redis):
        limiter = RateLimiter(mock_redis)
        # 5 requests with limit 10: should not raise
        mock_redis.incr.return_value = 5
        await limiter.check("test_key", limit=10, window_seconds=60)
        mock_redis.incr.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_sets_ttl_on_first_request(self, mock_redis):
        limiter = RateLimiter(mock_redis)
        mock_redis.incr.return_value = 1
        await limiter.check("new_window_key", limit=20, window_seconds=60)
        mock_redis.expire.assert_called_once_with("new_window_key", 60)

    @pytest.mark.asyncio
    async def test_blocks_and_raises_429_over_quota(self, mock_redis):
        limiter = RateLimiter(mock_redis)
        mock_redis.incr.return_value = 21  # Over limit of 20
        mock_redis.ttl.return_value = 35

        with pytest.raises(HTTPException) as exc_info:
            await limiter.check("exceeded_key", limit=20, window_seconds=60)

        assert exc_info.value.status_code == 429
        assert exc_info.value.headers["Retry-After"] == "35"
        assert "Rate limit exceeded" in exc_info.value.detail

    def test_plan_limits_configuration(self):
        """Verify tiered plan configuration values."""
        assert "free" in PLAN_LIMITS
        assert "pro" in PLAN_LIMITS
        assert "enterprise" in PLAN_LIMITS
        assert PLAN_LIMITS["free"]["rpm"] < PLAN_LIMITS["pro"]["rpm"]
        assert PLAN_LIMITS["pro"]["rpm"] < PLAN_LIMITS["enterprise"]["rpm"]

    @pytest.mark.asyncio
    async def test_dependency_skips_when_redis_none(self):
        """Fail-open: When redis_client is None on app, allows request through."""
        request = MagicMock()
        request.app.redis_client = None

        user = MagicMock()
        user.plan = "free"

        # Should complete without error
        await rate_limit_dependency(request=request, user=user)

    @pytest.mark.asyncio
    async def test_dependency_fails_open_on_redis_error(self, mock_redis):
        """Fail-open: Redis connection error does not crash the request."""
        mock_redis.incr.side_effect = ConnectionError("Redis cluster unavailable")
        request = MagicMock()
        request.app.redis_client = mock_redis

        user = MagicMock()
        user.user_id = "user-123"
        user.plan = "free"

        # Should log and swallow error rather than failing request
        await rate_limit_dependency(request=request, user=user)
