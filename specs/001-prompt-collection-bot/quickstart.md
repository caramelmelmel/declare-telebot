# Quickstart: Telegram Prompt Collection

Validates the feature end-to-end against spec.md's acceptance scenarios and success criteria.

## Prerequisites

- Docker and Docker Compose installed.
- A Telegram bot token from [@BotFather](https://t.me/BotFather) (`/newbot`).
- A personal Telegram account to act as the test user, able to open a chat with your new bot.

## Setup

1. Copy the example environment file and fill in your bot token:
   ```bash
   cp .env.example .env
   # set TELEGRAM_BOT_TOKEN=<token from BotFather>
   ```
2. Start the full stack (app, PostgreSQL, Redis, MinIO):
   ```bash
   docker compose -f docker/docker-compose.yml up --build
   ```
3. Run database migrations (creates the `User`/`Prompt` tables per data-model.md):
   ```bash
   docker compose -f docker/docker-compose.yml exec app alembic upgrade head
   ```
4. Choose a delivery mode for this local run:
   - **Local/dev (simplest)**: set `TELEGRAM_MODE=polling` in `.env` before starting — no public
     HTTPS endpoint needed (research.md §2, dev-only fallback).
   - **Webhook (matches production)**: expose the app's `/prompt` port via a tunnel
     (e.g. `ngrok http 8000`) and register it with Telegram:
     ```bash
     curl -F "url=https://<your-tunnel>/prompt" \
          -F "secret_token=<your configured secret>" \
          "https://api.telegram.org/bot<token>/setWebhook"
     ```

## Validate: User Story 1 — capture + acknowledgment (P1)

1. In Telegram, open a chat with your bot and send: `Hello bot`.
2. **Expect**: the bot replies with a receipt acknowledgment within a few seconds (SC-001).
3. Confirm it was captured:
   ```bash
   docker compose -f docker/docker-compose.yml exec postgres \
     psql -U app -d app -c "select user_id, content, received_at from prompt order by received_at desc limit 1;"
   ```
   **Expect**: one row with `content = 'Hello bot'` and your Telegram user ID.
4. Send a second message, e.g. `Second message`, and re-run the query.
   **Expect**: two distinct rows for your user, both preserved (spec.md Acceptance Scenario 2).

## Validate: User Story 2 — restart recovery (P2)

1. Restart just the app container:
   ```bash
   docker compose -f docker/docker-compose.yml restart app
   ```
2. Within 1 minute of the restart, send another message to the bot.
   **Expect**: `GET /healthz` returns `200 OK` again, and the bot acknowledges the new message
   normally (SC-005).
3. (Webhook mode only) Stop the `app` container, send a message from Telegram, wait 15 seconds,
   then start `app` again.
   **Expect**: once back up, the message sent during the outage is still captured (FR-006),
   because Telegram redelivers it — confirm via the same `psql` query as above.

## Validate: User Story 3 — non-text / empty input (P3)

1. Send a sticker or photo to the bot.
   **Expect**: the bot replies explaining only text prompts are supported (FR-007); the `psql`
   query above shows no new row for it (SC-003).
2. Send a message containing only spaces.
   **Expect**: the bot asks you to send actual content (FR-008); no new row is created.

## Validate: retention (FR-009, SC-006)

Retention spans 30 days, so this is validated at the unit/integration-test level
(`tests/unit`, `tests/integration`) rather than manually here: a test seeds a `Prompt` with
`received_at` 31 days in the past, runs `jobs/retention_cleanup.py`, and asserts the row (and
its MinIO object) are gone while a fresher row is untouched.

## Teardown

```bash
docker compose -f docker/docker-compose.yml down -v
```
