import pytest
from httpx import ASGITransport, AsyncClient

from src.api.app import create_app
from src.cache.in_memory_cache import InMemoryDedupCache
from src.repositories.in_memory_repository import InMemoryPayloadStore, InMemoryPromptRepository
from tests.fakes import FakePromptSource, make_telegram_update

SECRET = "changeme"


def build_app():
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
    return app, prompt_source, repository


@pytest.mark.asyncio
async def test_photo_message_gets_rejection_reply_and_is_not_captured():
    app, prompt_source, repository = build_app()
    update = make_telegram_update(
        update_id=3001,
        chat_id=900,
        user_id=900,
        text=None,
        extra_message_fields={
            "photo": [{"file_id": "abc", "file_unique_id": "abc1", "width": 90, "height": 90}]
        },
    )

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/prompt", json=update, headers={"X-Telegram-Bot-Api-Secret-Token": SECRET}
            )

    assert response.status_code == 200
    assert len(repository.prompts) == 0
    assert len(prompt_source.sent_messages) == 1
    assert "text" in prompt_source.sent_messages[0][1].lower()


@pytest.mark.asyncio
async def test_sticker_message_gets_rejection_reply_and_is_not_captured():
    app, prompt_source, repository = build_app()
    update = make_telegram_update(
        update_id=3002,
        chat_id=901,
        user_id=901,
        text=None,
        extra_message_fields={
            "sticker": {
                "file_id": "s1",
                "file_unique_id": "s1u",
                "width": 512,
                "height": 512,
                "is_animated": False,
                "is_video": False,
                "type": "regular",
            }
        },
    )

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/prompt", json=update, headers={"X-Telegram-Bot-Api-Secret-Token": SECRET}
            )

    assert response.status_code == 200
    assert len(repository.prompts) == 0
    assert len(prompt_source.sent_messages) == 1
