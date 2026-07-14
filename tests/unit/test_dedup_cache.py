import pytest

from src.cache.in_memory_cache import InMemoryDedupCache


@pytest.mark.asyncio
async def test_seen_or_mark_returns_false_then_true_for_same_update_id():
    cache = InMemoryDedupCache()

    first = await cache.seen_or_mark(123)
    second = await cache.seen_or_mark(123)

    assert first is False
    assert second is True


@pytest.mark.asyncio
async def test_seen_or_mark_treats_different_update_ids_independently():
    cache = InMemoryDedupCache()

    assert await cache.seen_or_mark(1) is False
    assert await cache.seen_or_mark(2) is False
    assert await cache.seen_or_mark(1) is True
    assert await cache.seen_or_mark(2) is True
