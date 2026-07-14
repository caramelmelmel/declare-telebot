from abc import ABC, abstractmethod
from datetime import datetime

from src.models.prompt import Prompt
from src.models.user import User


class PromptRepository(ABC):
    """Durable relational storage for captured prompts and their senders."""

    @abstractmethod
    async def save_prompt(self, prompt: Prompt, user: User) -> bool:
        """Persist `prompt` and upsert `user`.

        Returns False (no-op) if `prompt.telegram_update_id` was already stored
        (dedup backstop), True if a new row was created.
        """

    @abstractmethod
    async def list_expired_prompts(self, older_than: datetime) -> list[Prompt]:
        """Return prompts whose expires_at is at or before `older_than`."""

    @abstractmethod
    async def delete_prompt(self, prompt_id) -> None:
        """Remove a prompt row by id."""

    @abstractmethod
    async def ping(self) -> bool:
        """Return True if the backing store is reachable."""


class PayloadStore(ABC):
    """Durable object storage for the raw incoming update payload."""

    @abstractmethod
    async def put_raw_payload(self, object_key: str, payload: bytes) -> None:
        """Store the raw payload bytes under `object_key`."""

    @abstractmethod
    async def delete_raw_payload(self, object_key: str) -> None:
        """Remove the raw payload object, if present."""

    @abstractmethod
    async def ping(self) -> bool:
        """Return True if the backing store is reachable."""
