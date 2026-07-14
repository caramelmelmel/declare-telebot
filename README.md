# Telegram Bible Bot — Prompt Collection

A Python Telegram bot service that reliably captures every text message ("prompt") a user
sends it in a direct chat, acknowledges receipt, rejects non-text/empty input with a clear
explanation, and stores each captured prompt durably for 30 days.

See `specs/001-prompt-collection-bot/` for the full spec, plan, research, data model, and
API contract behind this implementation.

## Stack

- **FastAPI** — webhook receiver (`POST /prompt`) and health check (`GET /healthz`)
- **python-telegram-bot** — Telegram Bot API client
- **PostgreSQL** (SQLAlchemy async + Alembic) — durable `User`/`Prompt` records
- **MinIO** — durable raw Telegram update payload objects (30-day lifecycle expiry)
- **Redis** — ephemeral dedup cache guarding against Telegram's at-least-once webhook redelivery
- **Docker / docker-compose** — local dev and deployment

## Local development

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Run the test suite:

```bash
pytest
```

Lint:

```bash
ruff check src tests
```

Run the full stack with Docker (requires a Telegram bot token — see `.env.example`):

```bash
cp .env.example .env  # then fill in TELEGRAM_BOT_TOKEN
docker compose -f docker/docker-compose.yml up --build
docker compose -f docker/docker-compose.yml exec app alembic upgrade head
```

Full end-to-end validation steps (message capture, restart recovery, non-text rejection,
retention) are documented in
[`specs/001-prompt-collection-bot/quickstart.md`](specs/001-prompt-collection-bot/quickstart.md).

## Project structure

```text
src/
├── bot/            # PromptSource port + TelegramPromptSource adapter, message handlers
├── api/            # FastAPI app, POST /prompt webhook, GET /healthz
├── models/         # User, Prompt ORM models
├── repositories/   # PromptRepository/PayloadStore ports + Postgres/MinIO/in-memory adapters
├── cache/          # DedupCache port + Redis/in-memory adapters
├── services/       # PromptCaptureService (orchestration)
├── jobs/           # retention_cleanup (30-day expiry job)
└── db/             # SQLAlchemy session/engine

tests/
├── contract/       # FastAPI endpoint contract tests (fake adapters)
├── unit/           # service/handler/adapter unit tests (fake adapters)
└── integration/    # reserved for testcontainers-based tests (see Known gaps)
```

## Known gaps

This was built in a sandbox without a Docker daemon available, so the testcontainers-based
integration tests specified in `tasks.md` (T021, T029's original form, T031, T041's original
form) were adapted or deferred:

- Capture→Postgres/MinIO and dedup→redelivery behavior are covered instead by contract/unit
  tests against fake adapters (`tests/contract/`, `tests/unit/`).
- Restart-recovery (T031) has no automated coverage yet — it inherently requires a real
  running process/container to restart.
- Retention cleanup (T041) is covered by a unit test against fake adapters instead of real
  Postgres/MinIO.

Before shipping to production, run the real testcontainers-based integration suite and the
full `quickstart.md` walkthrough against Docker + a real Telegram bot token.
