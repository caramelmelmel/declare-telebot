import uuid
from datetime import UTC, datetime, timedelta

import pytest

from src.jobs.retention_cleanup import run_cleanup
from src.models.prompt import Prompt
from src.repositories.in_memory_repository import InMemoryPayloadStore, InMemoryPromptRepository


def make_prompt(update_id: int, days_old: int) -> Prompt:
    now = datetime.now(UTC)
    received_at = now - timedelta(days=days_old)
    return Prompt(
        id=uuid.uuid4(),
        user_id=1,
        chat_id=1,
        telegram_update_id=update_id,
        telegram_message_id=1,
        content="hello",
        raw_payload_object_key=f"{update_id}.json",
        received_at=received_at,
        expires_at=received_at + timedelta(days=30),
    )


@pytest.mark.asyncio
async def test_run_cleanup_removes_expired_prompt_and_its_payload():
    repository = InMemoryPromptRepository()
    payload_store = InMemoryPayloadStore()

    expired = make_prompt(update_id=1, days_old=31)
    fresh = make_prompt(update_id=2, days_old=1)

    for p in (expired, fresh):
        await payload_store.put_raw_payload(p.raw_payload_object_key, b"{}")
        repository.prompts[str(p.id)] = p
        repository._seen_update_ids.add(p.telegram_update_id)

    deleted_count = await run_cleanup(repository, payload_store)

    assert deleted_count == 1
    assert str(expired.id) not in repository.prompts
    assert expired.raw_payload_object_key not in payload_store.objects
    assert str(fresh.id) in repository.prompts
    assert fresh.raw_payload_object_key in payload_store.objects


@pytest.mark.asyncio
async def test_run_cleanup_is_a_noop_when_nothing_expired():
    repository = InMemoryPromptRepository()
    payload_store = InMemoryPayloadStore()

    fresh = make_prompt(update_id=3, days_old=1)
    await payload_store.put_raw_payload(fresh.raw_payload_object_key, b"{}")
    repository.prompts[str(fresh.id)] = fresh
    repository._seen_update_ids.add(fresh.telegram_update_id)

    deleted_count = await run_cleanup(repository, payload_store)

    assert deleted_count == 0
    assert str(fresh.id) in repository.prompts
