import pytest
from httpx import ASGITransport, AsyncClient

from src.api.app import create_app
from src.cache.in_memory_cache import InMemoryDedupCache
from src.repositories.in_memory_repository import InMemoryPayloadStore, InMemoryPromptRepository
from tests.fakes import FakePromptSource, make_telegram_update

SECRET = "changeme"


@pytest.mark.asyncio
async def test_whitespace_only_message_gets_rejection_reply_and_is_not_captured():
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
    update = make_telegram_update(update_id=4001, chat_id=902, user_id=902, text="   ")

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/prompt", json=update, headers={"X-Telegram-Bot-Api-Secret-Token": SECRET}
            )

    assert response.status_code == 200
    assert len(repository.prompts) == 0
    assert len(prompt_source.sent_messages) == 1
    assert "send" in prompt_source.sent_messages[0][1].lower()
