from telegram import Update

from src.bot.ports import PromptSource
from src.services.prompt_capture_service import PromptCaptureService

NON_TEXT_REJECTION_TEXT = (
    "Sorry, I can only accept text prompts right now — photos, stickers, voice notes, "
    "and other content types aren't supported yet."
)
EMPTY_TEXT_REJECTION_TEXT = "That message looks empty — please send some actual text."


async def handle_text_message(
    update: Update, raw_payload: bytes, capture_service: PromptCaptureService
) -> None:
    """Route a non-empty text message to the capture service (FR-002/FR-003/FR-004)."""
    message = update.message
    user = message.from_user

    await capture_service.capture(
        update_id=update.update_id,
        chat_id=message.chat_id,
        user_id=user.id,
        username=user.username,
        display_name=user.full_name,
        message_id=message.message_id,
        text=message.text,
        raw_payload=raw_payload,
    )


async def handle_non_text_message(update: Update, prompt_source: PromptSource) -> None:
    """Reply explaining only text prompts are supported (FR-007). Nothing is captured."""
    await prompt_source.send_text_message(update.message.chat_id, NON_TEXT_REJECTION_TEXT)


async def handle_empty_text_message(update: Update, prompt_source: PromptSource) -> None:
    """Reply asking for real content (FR-008). Nothing is captured."""
    await prompt_source.send_text_message(update.message.chat_id, EMPTY_TEXT_REJECTION_TEXT)
