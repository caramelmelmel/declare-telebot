from redis.asyncio import Redis

from src.cache.ports import DedupCache

TTL_SECONDS = 24 * 60 * 60


class RedisDedupCache(DedupCache):
    """Real adapter: guards against reprocessing a redelivered update_id via Redis SET NX."""

    def __init__(self, redis_url: str) -> None:
        self._redis = Redis.from_url(redis_url)

    async def seen_or_mark(self, update_id: int) -> bool:
        key = f"dedup:update:{update_id}"
        was_set = await self._redis.set(key, "1", nx=True, ex=TTL_SECONDS)
        return not was_set

    async def ping(self) -> bool:
        try:
            return await self._redis.ping()
        except Exception:
            return False

    async def close(self) -> None:
        await self._redis.aclose()
