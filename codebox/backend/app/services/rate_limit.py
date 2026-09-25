"""Fixed-window rate limiting backed by Redis (shared by all API processes).

Fails open: if Redis is unavailable, requests are allowed (the execution queue
itself will then report the outage)."""

import logging
import time

import redis
from fastapi import HTTPException, Request, status

from ..config import get_settings

log = logging.getLogger(__name__)
_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.Redis.from_url(get_settings().redis_url, socket_connect_timeout=1,
                                       socket_timeout=1)
    return _client


def hit(key: str, limit: int, window_seconds: int) -> bool:
    """Record one hit; return False if `key` exceeded `limit` in the current window."""
    bucket = int(time.time() // window_seconds)
    name = f"ratelimit:{key}:{bucket}"
    try:
        pipe = get_redis().pipeline()
        pipe.incr(name)
        pipe.expire(name, window_seconds + 1)
        count, _ = pipe.execute()
    except redis.RedisError as exc:
        log.debug("Rate limiter unavailable: %s", exc)
        return True
    return int(count) <= limit


def enforce(key: str, limit: int, window_seconds: int = 60) -> None:
    if not hit(key, limit, window_seconds):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            "Too many requests; please slow down and try again shortly",
                            headers={"Retry-After": str(window_seconds)})


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"
