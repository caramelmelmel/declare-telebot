from abc import ABC, abstractmethod


class DedupCache(ABC):
    """Ephemeral guard against re-processing a redelivered Telegram update."""

    @abstractmethod
    async def seen_or_mark(self, update_id: int) -> bool:
        """Atomically check-and-mark `update_id` as seen.

        Returns True if it was already seen (duplicate — caller should skip
        processing), False if this call newly marked it (caller should proceed).
        """

    @abstractmethod
    async def ping(self) -> bool:
        """Return True if the backing cache is reachable."""
