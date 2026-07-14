import logging
import uuid
from datetime import UTC, datetime, timedelta

from src.bot.ports import PromptSource
from src.models.prompt import Prompt
from src.models.user import User
from src.repositories.ports import PayloadStore, PromptRepository

logger = logging.getLogger(__name__)

ACKNOWLEDGMENT_TEXT = "Got it — your message has been received."


class PromptCaptureService:
    """Orchestrates capturing a text prompt: persistence, raw payload storage, and
    acknowledgment. Depends only on ports, so it is fully unit-testable against
    in-memory fakes (Constitution Principle I)."""

    def __init__(
        self,
        repository: PromptRepository,
        payload_store: PayloadStore,
        prompt_source: PromptSource,
        retention_days: int,
    ) -> None:
        self._repository = repository
        self._payload_store = payload_store
        self._prompt_source = prompt_source
        self._retention_days = retention_days

    async def capture(
        self,
        *,
        update_id: int,
        chat_id: int,
        user_id: int,
        username: str | None,
        display_name: str | None,
        message_id: int,
        text: str,
        raw_payload: bytes,
    ) -> Prompt | None:
        now = datetime.now(UTC)
        object_key = f"{update_id}.json"

        prompt = Prompt(
            id=uuid.uuid4(),
            user_id=user_id,
            chat_id=chat_id,
            telegram_update_id=update_id,
            telegram_message_id=message_id,
            content=text,
            raw_payload_object_key=object_key,
            received_at=now,
            expires_at=now + timedelta(days=self._retention_days),
        )
        user = User(
            telegram_user_id=user_id,
            username=username,
            display_name=display_name,
            first_seen_at=now,
            last_seen_at=now,
        )

        logger.info("prompt.received", extra={"update_id": update_id, "user_id": user_id})

        await self._payload_store.put_raw_payload(object_key, raw_payload)
        created = await self._repository.save_prompt(prompt, user)
        if not created:
            logger.info("prompt.duplicate", extra={"update_id": update_id})
            return None

        logger.info("prompt.persisted", extra={"update_id": update_id, "prompt_id": str(prompt.id)})

        await self._prompt_source.send_text_message(chat_id, ACKNOWLEDGMENT_TEXT)
        logger.info("prompt.acknowledged", extra={"update_id": update_id, "chat_id": chat_id})

        return prompt
