import time

from ..core.config import settings


class Cache:
    """Redis when REDIS_URL is reachable, otherwise a small in-process fallback."""

    def __init__(self, url: str | None):
        self._r = None
        self._mem: dict[str, tuple[str, float]] = {}
        if url:
            try:
                import redis

                self._r = redis.Redis.from_url(url, decode_responses=True)
                self._r.ping()
            except Exception:
                self._r = None

    @property
    def backend(self) -> str:
        return "redis" if self._r else "memory"

    def get(self, key: str) -> str | None:
        if self._r:
            return self._r.get(key)
        item = self._mem.get(key)
        if item and item[1] > time.time():
            return item[0]
        self._mem.pop(key, None)
        return None

    def set(self, key: str, value: str, ttl: int) -> None:
        if self._r:
            self._r.set(key, value, ex=ttl)
        else:
            self._mem[key] = (value, time.time() + ttl)

    def incr(self, key: str, ttl: int) -> int:
        if self._r:
            pipe = self._r.pipeline()
            pipe.incr(key)
            pipe.expire(key, ttl, nx=True)
            return int(pipe.execute()[0])
        current = int(self.get(key) or 0) + 1
        item = self._mem.get(key)
        expires = item[1] if item else time.time() + ttl
        self._mem[key] = (str(current), expires)
        return current


cache = Cache(settings.redis_url)
