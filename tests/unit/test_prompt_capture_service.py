from datetime import UTC, datetime, timedelta

import pytest

from src.repositories.in_memory_repository import InMemoryPayloadStore, InMemoryPromptRepository
from src.services.prompt_capture_service import PromptCaptureService
from tests.fakes import FakePromptSource


def make_service():
    repository = InMemoryPromptRepository()
    payload_store = InMemoryPayloadStore()
    prompt_source = FakePromptSource()
    service = PromptCaptureService(
        repository=repository,
        payload_store=payload_store,
        prompt_source=prompt_source,
        retention_days=30,
    )
    return service, repository, payload_store, prompt_source


@pytest.mark.asyncio
async def test_capture_persists_prompt_and_sends_acknowledgment():
    service, repository, payload_store, prompt_source = make_service()

    prompt = await service.capture(
        update_id=42,
        chat_id=100,
        user_id=100,
        username="alice",
        display_name="Alice",
        message_id=7,
        text="Hello there",
        raw_payload=b'{"update_id": 42}',
    )

    assert prompt is not None
    assert len(repository.prompts) == 1
    stored = repository.prompts[str(prompt.id)]
    assert stored.content == "Hello there"
    assert stored.user_id == 100
    assert stored.chat_id == 100
    assert stored.telegram_update_id == 42

    assert 100 in repository.users
    assert repository.users[100].username == "alice"

    assert len(payload_store.objects) == 1
    assert prompt.raw_payload_object_key in payload_store.objects

    assert len(prompt_source.sent_messages) == 1
    assert prompt_source.sent_messages[0][0] == 100


@pytest.mark.asyncio
async def test_capture_sets_expires_at_30_days_after_received_at():
    service, _, _, _ = make_service()

    before = datetime.now(UTC)
    prompt = await service.capture(
        update_id=43,
        chat_id=101,
        user_id=101,
        username=None,
        display_name="Bob",
        message_id=1,
        text="hi",
        raw_payload=b"{}",
    )
    after = datetime.now(UTC)

    expected_min = before + timedelta(days=30)
    expected_max = after + timedelta(days=30)
    assert expected_min <= prompt.expires_at <= expected_max


@pytest.mark.asyncio
async def test_capture_is_idempotent_for_duplicate_update_id():
    service, repository, payload_store, prompt_source = make_service()

    await service.capture(
        update_id=44,
        chat_id=102,
        user_id=102,
        username="carol",
        display_name="Carol",
        message_id=1,
        text="first",
        raw_payload=b"{}",
    )
    result = await service.capture(
        update_id=44,
        chat_id=102,
        user_id=102,
        username="carol",
        display_name="Carol",
        message_id=1,
        text="first",
        raw_payload=b"{}",
    )

    assert result is None
    assert len(repository.prompts) == 1
    assert len(prompt_source.sent_messages) == 1
