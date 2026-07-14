import pytest
from httpx import ASGITransport, AsyncClient

from src.api.app import create_app
from src.cache.in_memory_cache import InMemoryDedupCache
from src.repositories.in_memory_repository import InMemoryPayloadStore, InMemoryPromptRepository
from tests.fakes import FakePromptSource, make_telegram_update

SECRET = "changeme"


@pytest.mark.asyncio
async def test_redelivered_update_is_processed_once_only():
    prompt_source = FakePromptSource()
    repository = InMemoryPromptRepository()
    app = create_app(
        overrides={
            "prompt_source": prompt_source,
            "prompt_repository": repository,
            "payload_store": InMemoryPayloadStore(),
            "dedup_cache": InMemoryDedupCache(),
        }
    )

    update = make_telegram_update(update_id=2001, chat_id=777, user_id=777, text="Retry me")

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            headers = {"X-Telegram-Bot-Api-Secret-Token": SECRET}
            first = await client.post("/prompt", json=update, headers=headers)
            second = await client.post("/prompt", json=update, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert len(repository.prompts) == 1
    assert len(prompt_source.sent_messages) == 1


@pytest.mark.asyncio
async def test_dedup_cache_short_circuits_before_any_processing():
    """Distinct from the DB-level backstop: a pre-seeded dedup cache must stop
    processing before the repository/payload-store are touched at all."""
    prompt_source = FakePromptSource()
    repository = InMemoryPromptRepository()
    payload_store = InMemoryPayloadStore()
    dedup_cache = InMemoryDedupCache()

    app = create_app(
        overrides={
            "prompt_source": prompt_source,
            "prompt_repository": repository,
            "payload_store": payload_store,
            "dedup_cache": dedup_cache,
        }
    )

    update = make_telegram_update(update_id=2002, chat_id=778, user_id=778, text="Already seen")

    async with app.router.lifespan_context(app):
        await dedup_cache.seen_or_mark(2002)  # pre-seed as already processed

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/prompt",
                json=update,
                headers={"X-Telegram-Bot-Api-Secret-Token": SECRET},
            )

    assert response.status_code == 200
    assert len(repository.prompts) == 0
    assert len(payload_store.objects) == 0
    assert len(prompt_source.sent_messages) == 0
