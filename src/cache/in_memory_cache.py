from src.cache.ports import DedupCache


class InMemoryDedupCache(DedupCache):
    """Test fake: keeps seen update_ids in a process-memory set instead of Redis."""

    def __init__(self) -> None:
        self._seen: set[int] = set()

    async def seen_or_mark(self, update_id: int) -> bool:
        if update_id in self._seen:
            return True
        self._seen.add(update_id)
        return False

    async def ping(self) -> bool:
        return True
