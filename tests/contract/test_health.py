import pytest
from httpx import ASGITransport, AsyncClient

from src.api.app import create_app
from src.cache.in_memory_cache import InMemoryDedupCache
from src.repositories.in_memory_repository import InMemoryPayloadStore, InMemoryPromptRepository
from tests.fakes import FakePromptSource


class AlwaysDownDedupCache(InMemoryDedupCache):
    async def ping(self) -> bool:
        return False


def build_app(dedup_cache):
    return create_app(
        overrides={
            "prompt_source": FakePromptSource(),
            "prompt_repository": InMemoryPromptRepository(),
            "payload_store": InMemoryPayloadStore(),
            "dedup_cache": dedup_cache,
        }
    )


@pytest.mark.asyncio
async def test_healthz_returns_200_when_all_dependencies_reachable():
    app = build_app(InMemoryDedupCache())

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_healthz_returns_503_when_a_dependency_is_unreachable():
    app = build_app(AlwaysDownDedupCache())

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/healthz")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["detail"] == "redis"
