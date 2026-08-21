"""Redis-backed sliding-window rate limiter, plan-aware.

Usage (as a FastAPI dependency)::

    @router.post("/endpoint")
    async def my_handler(
        request: Request,
        _: None = Depends(rate_limit_dependency),
    ):
        ...

``rate_limit_dependency`` reads the authenticated user's ``plan`` attribute
and enforces per-minute and per-day request caps.  The counters live in Redis
under keys of the form ``rl:<user_id>:minute:<bucket>`` and
``rl:<user_id>:day:<bucket>``, where *bucket* is an integer epoch divided by
the window size so that counters are auto-scoped per time window.
"""

import time
import logging

from fastapi import Request, HTTPException, status, Depends
from redis.asyncio import Redis

from helpers.security import get_current_user

log = logging.getLogger("uvicorn.error")

# ---------------------------------------------------------------------------
# Plan-based quota table
# ---------------------------------------------------------------------------
#
# Adjust these figures to match commercial SLAs.  New plans can be added
# without changing the dependency function below.
PLAN_LIMITS: dict[str, dict[str, int]] = {
    "free":       {"rpm": 20,  "rpd": 200},
    "pro":        {"rpm": 120, "rpd": 5_000},
    "enterprise": {"rpm": 600, "rpd": 50_000},
}

# Fallback when a user's plan is not in the table (treated as free).
_DEFAULT_PLAN = "free"


# ---------------------------------------------------------------------------
# Core rate-limiter class
# ---------------------------------------------------------------------------

class RateLimiter:
    """Thin wrapper around a Redis incr/expire sliding-counter pattern."""

    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def check(self, key: str, limit: int, window_seconds: int) -> None:
        """Increment *key* and raise 429 if the counter exceeds *limit*.

        Args:
            key:            Redis key (includes user ID + time bucket).
            limit:          Maximum allowed requests in the window.
            window_seconds: TTL applied when the key is first created.

        Raises:
            HTTPException(429): when the limit has been exceeded.
        """
        current: int = await self.redis.incr(key)
        if current == 1:
            # First request in this window — set the expiry.
            await self.redis.expire(key, window_seconds)
        if current > limit:
            ttl: int = await self.redis.ttl(key)
            log.warning("Rate limit exceeded for key=%s current=%d limit=%d", key, current, limit)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please slow down.",
                headers={"Retry-After": str(max(ttl, 1))},
            )


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

async def rate_limit_dependency(
    request: Request,
    user=Depends(get_current_user),
) -> None:
    """FastAPI dependency that enforces per-plan RPM and RPD caps.

    Reads ``request.app.redis_client`` so the Redis connection must be
    initialised during the app lifespan (see ``src/main.py``).

    Raises:
        HTTPException(429): when the per-minute or per-day quota is exceeded.
        HTTPException(503): when Redis is unavailable (fail-open to avoid
                            blocking all requests if Redis goes down).
    """
    redis_client: Redis | None = getattr(request.app, "redis_client", None)
    if redis_client is None:
        # Redis not configured — log a warning and allow the request through
        # rather than hard-blocking all traffic.
        log.warning("rate_limit_dependency: redis_client not found on app; skipping rate check")
        return

    plan: str = getattr(user, "plan", _DEFAULT_PLAN) or _DEFAULT_PLAN
    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS[_DEFAULT_PLAN])

    limiter = RateLimiter(redis_client)

    minute_bucket = int(time.time() // 60)
    day_bucket = int(time.time() // 86_400)

    minute_key = f"rl:{user.user_id}:minute:{minute_bucket}"
    day_key = f"rl:{user.user_id}:day:{day_bucket}"

    try:
        await limiter.check(minute_key, limits["rpm"], window_seconds=60)
        await limiter.check(day_key, limits["rpd"], window_seconds=86_400)
    except HTTPException:
        raise
    except Exception as exc:
        # Redis error — log and fail-open so Redis outage ≠ site outage.
        log.error("Rate limiter Redis error: %s", exc, exc_info=True)
