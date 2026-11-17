import time
from collections import defaultdict, deque
from typing import Deque, Dict, Optional, Tuple
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from app.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach defensive HTTP security headers to all API responses."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "geolocation=(), microphone=(), camera=()",
        )
        if request.url.path.startswith(f"{settings.API_V1_STR}/auth"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding-window rate limiter for authentication and AI endpoints.
    Uses Redis when reachable and falls back cleanly to in-memory tracking.
    """

    def __init__(self, app):
        super().__init__(app)
        self._memory_buckets: Dict[str, Deque[float]] = defaultdict(deque)
        self._redis_client = None
        self._redis_checked_at: float = 0.0

    def _get_limit_for_path(self, path: str) -> Optional[Tuple[str, int]]:
        if path.startswith(f"{settings.API_V1_STR}/auth/"):
            return ("auth", settings.AUTH_RATE_LIMIT_PER_MINUTE)
        if path.startswith(f"{settings.API_V1_STR}/intelligence/assistant/"):
            return ("ai", settings.AI_RATE_LIMIT_PER_MINUTE)
        return None

    async def _check_redis(self, key: str, limit: int, window_seconds: int) -> Optional[bool]:
        now = time.time()
        # Re-check Redis availability at most once every 30s if previously unavailable
        if self._redis_client is None and (now - self._redis_checked_at) < 30.0:
            return None

        try:
            if self._redis_client is None:
                import redis.asyncio as aioredis

                self._redis_checked_at = now
                client = aioredis.from_url(settings.redis_url, socket_connect_timeout=0.5, socket_timeout=0.5)
                await client.ping()
                self._redis_client = client

            pipe = self._redis_client.pipeline()
            pipe.incr(key)
            pipe.expire(key, window_seconds, nx=True)
            count, _ = await pipe.execute()
            return int(count) <= limit
        except Exception:
            self._redis_client = None
            self._redis_checked_at = now
            return None

    def _check_memory(self, key: str, limit: int, window_seconds: int) -> bool:
        now = time.monotonic()
        bucket = self._memory_buckets[key]
        cutoff = now - window_seconds
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= limit:
            return False
        bucket.append(now)
        return True

    async def dispatch(self, request: Request, call_next) -> Response:
        limit_cfg = self._get_limit_for_path(request.url.path)
        if not limit_cfg:
            return await call_next(request)

        scope, limit = limit_cfg
        forwarded_for = request.headers.get("X-Forwarded-For")
        client_ip = (
            forwarded_for.split(",")[0].strip()
            if forwarded_for
            else (request.client.host if request.client else "unknown")
        )
        window_seconds = 60
        bucket_key = f"ratelimit:{scope}:{client_ip}"

        allowed = await self._check_redis(bucket_key, limit, window_seconds)
        if allowed is None:
            allowed = self._check_memory(bucket_key, limit, window_seconds)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please retry shortly."},
                headers={"Retry-After": str(window_seconds)},
            )

        return await call_next(request)

