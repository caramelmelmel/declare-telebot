from src.bot.ports import PromptSource


class FakePromptSource(PromptSource):
    """Test double: records sent messages instead of calling the Telegram API."""

    def __init__(self) -> None:
        self.sent_messages: list[tuple[int, str]] = []

    async def send_text_message(self, chat_id: int, text: str) -> None:
        self.sent_messages.append((chat_id, text))


def make_telegram_update(
    update_id: int,
    chat_id: int,
    user_id: int,
    message_id: int = 1,
    text: str | None = None,
    username: str | None = "tester",
    first_name: str = "Test",
    extra_message_fields: dict | None = None,
) -> dict:
    """Build a minimal Telegram Update JSON payload for tests."""
    message: dict = {
        "message_id": message_id,
        "date": 1_700_000_000,
        "chat": {"id": chat_id, "type": "private"},
        "from": {
            "id": user_id,
            "is_bot": False,
            "first_name": first_name,
            "username": username,
        },
    }
    if text is not None:
        message["text"] = text
    if extra_message_fields:
        message.update(extra_message_fields)

    return {"update_id": update_id, "message": message}
