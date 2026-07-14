from datetime import datetime

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from src.db.session import session_scope
from src.models.prompt import Prompt
from src.models.user import User
from src.repositories.ports import PromptRepository


class PostgresPromptRepository(PromptRepository):
    """Real adapter: persists prompts/users in PostgreSQL."""

    async def save_prompt(self, prompt: Prompt, user: User) -> bool:
        async with session_scope() as session:
            existing_user = await session.get(User, user.telegram_user_id)
            if existing_user is None:
                session.add(user)
            else:
                existing_user.username = user.username
                existing_user.display_name = user.display_name
                existing_user.last_seen_at = user.last_seen_at

            await session.flush()
            session.add(prompt)
            try:
                await session.commit()
            except IntegrityError:
                # Duplicate telegram_update_id — dedup backstop (FR-006, research.md §3)
                await session.rollback()
                return False
        return True

    async def list_expired_prompts(self, older_than: datetime) -> list[Prompt]:
        async with session_scope() as session:
            result = await session.execute(select(Prompt).where(Prompt.expires_at <= older_than))
            return list(result.scalars().all())

    async def delete_prompt(self, prompt_id) -> None:
        async with session_scope() as session:
            prompt = await session.get(Prompt, prompt_id)
            if prompt is not None:
                await session.delete(prompt)
                await session.commit()

    async def ping(self) -> bool:
        try:
            async with session_scope() as session:
                await session.execute(text("SELECT 1"))
            return True
        except Exception:
            return False
