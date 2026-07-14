import pytest
from httpx import ASGITransport, AsyncClient

from src.api.app import create_app
from src.cache.in_memory_cache import InMemoryDedupCache
from src.repositories.in_memory_repository import InMemoryPayloadStore, InMemoryPromptRepository
from tests.fakes import FakePromptSource, make_telegram_update

SECRET = "changeme"


@pytest.mark.asyncio
async def test_post_prompt_with_text_message_returns_200_and_sends_ack():
    prompt_source = FakePromptSource()
    app = create_app(
        overrides={
            "prompt_source": prompt_source,
            "prompt_repository": InMemoryPromptRepository(),
            "payload_store": InMemoryPayloadStore(),
            "dedup_cache": InMemoryDedupCache(),
        }
    )

    update = make_telegram_update(update_id=1001, chat_id=555, user_id=555, text="Hello bot")

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/prompt",
                json=update,
                headers={"X-Telegram-Bot-Api-Secret-Token": SECRET},
            )

    assert response.status_code == 200
    assert len(prompt_source.sent_messages) == 1
    assert prompt_source.sent_messages[0][0] == 555


@pytest.mark.asyncio
async def test_post_prompt_without_secret_returns_401():
    app = create_app(
        overrides={
            "prompt_source": FakePromptSource(),
            "prompt_repository": InMemoryPromptRepository(),
            "payload_store": InMemoryPayloadStore(),
            "dedup_cache": InMemoryDedupCache(),
        }
    )
    update = make_telegram_update(update_id=1002, chat_id=555, user_id=555, text="Hello")

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/prompt", json=update)

    assert response.status_code == 401
