import logging

from fastapi import APIRouter, Header, HTTPException, Request, Response, FastAPI
from telegram import Update

from src.bot.handlers import (
    handle_empty_text_message,
    handle_non_text_message,
    handle_text_message,
)
from src.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter()


def _validate_secret(secret_header: str | None) -> None:
    settings = get_settings()
    expected = settings.telegram_webhook_secret
    if secret_header is None or not _constant_time_eq(secret_header, expected):
        raise HTTPException(status_code=401, detail="invalid secret token")


def _constant_time_eq(a: str, b: str) -> bool:
    import hmac

    return hmac.compare_digest(a, b)


@router.post("/prompt")
async def receive_update(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> Response:
    _validate_secret(x_telegram_bot_api_secret_token)

    raw_body = await request.body()
    body = await request.json()
    update = Update.de_json(body, bot=None)

    try:
        await _dispatch(request, update, raw_body=raw_body)
    except Exception:
        # Contract: always 200 once authenticated (see contracts/http-api.md) — a
        # non-200 here would make Telegram retry, and the update_id is already
        # marked seen, so a retry would just be silently dropped by dedup.
        logger.exception("webhook.dispatch_failed", extra={"update_id": update.update_id})

    return Response(status_code=200)


async def _dispatch(request_or_app: Request | FastAPI, update: Update, raw_body: bytes) -> None:
    """Route the parsed update to the appropriate handler.

    Populated incrementally by later tasks: dedup short-circuit (US2),
    non-text/empty rejection (US3).
    """
    app = request_or_app.app if hasattr(request_or_app, "app") else request_or_app
    dedup_cache = app.state.dedup_cache
    already_seen = await dedup_cache.seen_or_mark(update.update_id)
    if already_seen:
        return

    capture_service = app.state.capture_service
    prompt_source = app.state.prompt_source

    if update.message is None:
        return

    text = update.message.text
    if text is None:
        await handle_non_text_message(update, prompt_source)
    elif text.strip() == "":
        await handle_empty_text_message(update, prompt_source)
    else:
        await handle_text_message(update, raw_body, capture_service)
