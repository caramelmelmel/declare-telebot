from abc import ABC, abstractmethod


class PromptSource(ABC):
    """Outbound channel back to the messaging platform (e.g. Telegram)."""

    @abstractmethod
    async def send_text_message(self, chat_id: int, text: str) -> None:
        """Send a plain text message to the given chat (acknowledgment or rejection reply)."""
