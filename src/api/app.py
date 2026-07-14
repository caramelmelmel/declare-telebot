from contextlib import asynccontextmanager
from typing import Any


def _build_lifespan(overrides: dict[str, Any] | None):
    overrides = overrides or {}

    @asynccontextmanager
    async def lifespan(app):
        from src.config import get_settings
        from src.services.prompt_capture_service import PromptCaptureService

        settings = get_settings()

        if "prompt_source" in overrides:
            prompt_source = overrides["prompt_source"]
        else:
            from src.bot.telegram_adapter import TelegramPromptSource

            prompt_source = TelegramPromptSource(bot_token=settings.telegram_bot_token)

        if "prompt_repository" in overrides:
            prompt_repository = overrides["prompt_repository"]
        else:
            from src.repositories.postgres_repository import PostgresPromptRepository

            prompt_repository = PostgresPromptRepository()

        if "payload_store" in overrides:
            payload_store = overrides["payload_store"]
        else:
            from src.repositories.minio_payload_store import MinioPayloadStore

            payload_store = MinioPayloadStore(
                endpoint=settings.minio_endpoint,
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                bucket=settings.minio_bucket,
                secure=settings.minio_secure,
                retention_days=settings.prompt_retention_days,
            )

        if "dedup_cache" in overrides:
            dedup_cache = overrides["dedup_cache"]
        else:
            from src.cache.redis_cache import RedisDedupCache

            dedup_cache = RedisDedupCache(redis_url=settings.redis_url)

        app.state.prompt_source = prompt_source
        app.state.prompt_repository = prompt_repository
        app.state.payload_store = payload_store
        app.state.dedup_cache = dedup_cache
        app.state.capture_service = PromptCaptureService(
            repository=prompt_repository,
            payload_store=payload_store,
            prompt_source=prompt_source,
            retention_days=settings.prompt_retention_days,
        )

        polling_task = None
        if settings.telegram_mode == "polling" and "prompt_source" not in overrides:
            import asyncio
            import json
            import logging
            from telegram import Bot
            from src.api.webhook import _dispatch

            logger = logging.getLogger(__name__)

            async def polling_loop():
                bot = Bot(token=settings.telegram_bot_token)
                try:
                    await bot.delete_webhook(drop_pending_updates=True)
                except Exception as e:
                    logger.warning(f"Failed to delete webhook: {e}")
                
                offset = 0
                logger.info("Starting Telegram bot long polling...")
                while True:
                    try:
                        updates = await bot.get_updates(offset=offset, timeout=10)
                        for update in updates:
                            offset = update.update_id + 1
                            raw_body = json.dumps(update.to_dict()).encode("utf-8")
                            await _dispatch(app, update, raw_body)
                    except asyncio.CancelledError:
                        break
                    except Exception as e:
                        logger.error(f"Error in polling loop: {e}")
                        await asyncio.sleep(2)

            polling_task = asyncio.create_task(polling_loop())
            app.state.polling_task = polling_task

        yield

        if polling_task is not None:
            polling_task.cancel()
            try:
                await polling_task
            except asyncio.CancelledError:
                pass

        close = getattr(dedup_cache, "close", None)
        if close is not None:
            await close()

    return lifespan


def create_app(overrides: dict[str, Any] | None = None):
    from fastapi import FastAPI

    app = FastAPI(title="Telegram Prompt Collection", lifespan=_build_lifespan(overrides))

    from src.api.health import router as health_router
    from src.api.webhook import router as webhook_router

    app.include_router(health_router)
    app.include_router(webhook_router)

    return app


app = create_app()
