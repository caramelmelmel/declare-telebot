from datetime import datetime

from src.models.prompt import Prompt
from src.models.user import User
from src.repositories.ports import PayloadStore, PromptRepository


class InMemoryPromptRepository(PromptRepository):
    """Test fake: keeps prompts/users in process memory instead of Postgres."""

    def __init__(self) -> None:
        self.prompts: dict[str, Prompt] = {}
        self.users: dict[int, User] = {}
        self._seen_update_ids: set[int] = set()

    async def save_prompt(self, prompt: Prompt, user: User) -> bool:
        if prompt.telegram_update_id in self._seen_update_ids:
            return False
        self._seen_update_ids.add(prompt.telegram_update_id)
        self.prompts[str(prompt.id)] = prompt

        existing = self.users.get(user.telegram_user_id)
        if existing is None:
            self.users[user.telegram_user_id] = user
        else:
            existing.username = user.username
            existing.display_name = user.display_name
            existing.last_seen_at = user.last_seen_at
        return True

    async def list_expired_prompts(self, older_than: datetime) -> list[Prompt]:
        return [p for p in self.prompts.values() if p.expires_at <= older_than]

    async def delete_prompt(self, prompt_id) -> None:
        self.prompts.pop(str(prompt_id), None)

    async def ping(self) -> bool:
        return True


class InMemoryPayloadStore(PayloadStore):
    """Test fake: keeps raw payloads in process memory instead of MinIO."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    async def put_raw_payload(self, object_key: str, payload: bytes) -> None:
        self.objects[object_key] = payload

    async def delete_raw_payload(self, object_key: str) -> None:
        self.objects.pop(object_key, None)

    async def ping(self) -> bool:
        return True
