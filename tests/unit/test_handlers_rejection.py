import pytest
from telegram import Update

from src.bot.handlers import handle_empty_text_message, handle_non_text_message
from tests.fakes import FakePromptSource, make_telegram_update


@pytest.mark.asyncio
async def test_handle_non_text_message_sends_text_only_explanation():
    prompt_source = FakePromptSource()
    update = Update.de_json(
        make_telegram_update(
            update_id=1,
            chat_id=10,
            user_id=10,
            text=None,
            extra_message_fields={"voice": {"file_id": "v", "file_unique_id": "vu", "duration": 3}},
        ),
        bot=None,
    )

    await handle_non_text_message(update, prompt_source)

    assert len(prompt_source.sent_messages) == 1
    chat_id, text = prompt_source.sent_messages[0]
    assert chat_id == 10
    assert "text" in text.lower()


@pytest.mark.asyncio
async def test_handle_empty_text_message_asks_for_real_content():
    prompt_source = FakePromptSource()
    update = Update.de_json(
        make_telegram_update(update_id=2, chat_id=11, user_id=11, text="   "), bot=None
    )

    await handle_empty_text_message(update, prompt_source)

    assert len(prompt_source.sent_messages) == 1
    chat_id, text = prompt_source.sent_messages[0]
    assert chat_id == 11
    assert "send" in text.lower()
