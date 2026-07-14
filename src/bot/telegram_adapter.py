from telegram import Bot

from src.bot.ports import PromptSource


class TelegramPromptSource(PromptSource):
    """Real adapter: sends replies via the Telegram Bot API."""

    def __init__(self, bot_token: str) -> None:
        self._bot = Bot(token=bot_token)

    async def send_text_message(self, chat_id: int, text: str) -> None:
        await self._bot.send_message(chat_id=chat_id, text=text)
