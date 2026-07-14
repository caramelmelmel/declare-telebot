import argparse
import asyncio
import logging
from src.config import get_settings
from src.repositories.minio_payload_store import MinioPayloadStore
from src.repositories.postgres_repository import PostgresPromptRepository
from src.config import get_settings
from src.repositories.minio_payload_store import MinioPayloadStore
from src.repositories.postgres_repository import PostgresPromptRepository
from datetime import UTC, datetime

from src.repositories.ports import PayloadStore, PromptRepository

logger = logging.getLogger(__name__)


async def run_cleanup(repository: PromptRepository, payload_store: PayloadStore) -> int:
    """Delete prompts (and their raw payloads) past their expires_at (FR-009, SC-006)."""
    now = datetime.now(UTC)
    expired = await repository.list_expired_prompts(older_than=now)

    for prompt in expired:
        await payload_store.delete_raw_payload(prompt.raw_payload_object_key)
        await repository.delete_prompt(prompt.id)
        logger.info("prompt.expired_deleted", extra={"prompt_id": str(prompt.id)})

    return len(expired)


async def _run_forever(interval_seconds: int) -> None:


    settings = get_settings()
    repository = PostgresPromptRepository()
    payload_store = MinioPayloadStore(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        bucket=settings.minio_bucket,
        secure=settings.minio_secure,
        retention_days=settings.prompt_retention_days,
    )

    while True:
        deleted = await run_cleanup(repository, payload_store)
        logger.info("retention_cleanup.run_complete", extra={"deleted": deleted})
        await asyncio.sleep(interval_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description="Delete expired captured prompts (FR-009).")
    parser.add_argument("--loop", action="store_true", help="Run forever on an interval")
    parser.add_argument("--interval-seconds", type=int, default=86400)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    if args.loop:
        asyncio.run(_run_forever(args.interval_seconds))
    else:
        settings = get_settings()
        repository = PostgresPromptRepository()
        payload_store = MinioPayloadStore(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            bucket=settings.minio_bucket,
            secure=settings.minio_secure,
            retention_days=settings.prompt_retention_days,
        )
        deleted = asyncio.run(run_cleanup(repository, payload_store))
        print(f"Deleted {deleted} expired prompt(s).")


if __name__ == "__main__":
    main()
