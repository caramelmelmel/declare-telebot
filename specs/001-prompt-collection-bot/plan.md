# Implementation Plan: Telegram Prompt Collection

**Branch**: `001-prompt-collection-bot` | **Date**: 2026-07-13 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-prompt-collection-bot/spec.md`

## Summary

Build a Python Telegram bot service that reliably captures every text message ("prompt") a
user sends it in a direct chat, acknowledges receipt, rejects non-text/empty input with a
clear explanation, and stores each captured prompt durably for 30 days. The service receives
Telegram updates via a FastAPI webhook, processes them with python-telegram-bot, persists
structured metadata in PostgreSQL and the raw payload in MinIO, and uses Redis to deduplicate
Telegram's at-least-once webhook redelivery. The whole stack runs in Docker containers. No
substantive reply/answer generation is in scope — this feature only captures and acknowledges.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: python-telegram-bot (Telegram Bot API client/handlers), FastAPI
(webhook HTTP receiver + health endpoint), SQLAlchemy (async) + Alembic (Postgres ORM/migrations),
redis-py (async) (dedup cache client), minio (Python SDK) (raw payload object storage client)

**Storage**: PostgreSQL (durable `User`/`Prompt` relational records, 30-day retention),
MinIO (durable raw Telegram update payload objects, 30-day lifecycle expiry), Redis (ephemeral
`update_id` dedup cache only — not a durable store)

**Testing**: pytest + pytest-asyncio (unit tests against in-memory fake adapters),
testcontainers-python (integration tests against real Postgres/Redis/MinIO containers),
httpx.AsyncClient (FastAPI webhook contract tests)

**Target Platform**: Linux server, deployed as Docker containers (docker-compose for local
dev/CI; the same built image is promoted through review to production per the constitution)

**Project Type**: Single backend service (web-service style: HTTP webhook receiver + bot logic,
no frontend)

**Performance Goals**: 99% of captured text messages acknowledged within 3 seconds (SC-001);
recovers from an unplanned restart and resumes accepting messages within 1 minute (SC-005)

**Constraints**: Must not permanently lose a message delivered while briefly unavailable, given
Telegram still has it queued (FR-006); must not double-process a redelivered update (research.md
§3); captured prompts and their raw payloads must auto-expire at 30 days (FR-009, SC-006)

**Scale/Scope**: Single bot, direct (1:1) chats only (group chats explicitly out of scope).
No specific concurrent-user target was given in the spec; reasonable default is a
small-to-moderate personal/community bot load (tens to low hundreds of concurrent users),
consistent with SC-004's 50-message verification sample.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
|---|---|---|
| I. Test-First Development (NON-NEGOTIABLE) | Every handler, repository, and adapter must be built test-first (failing test → implementation). Plan's Ports-and-Adapters design (research.md §9) exists specifically to make this possible without live external services. | **PASS** — enforced structurally; `/speckit-tasks` must order test tasks before implementation tasks for each unit. |
| II. Pattern-Driven Extensibility | New integrations must use an appropriate, non-speculative design pattern with ≥2 current/planned use cases. Ports-and-Adapters (research.md §9) is justified by two concrete present-day consumers per port: the real adapter and the test fake required by Principle I. | **PASS** |
| III. Review-Gated Production Releases (NON-NEGOTIABLE) | No design-time gate; enforced at delivery time (PR review + explicit approval before any deploy of the Docker image). Plan does not bypass this. | **PASS** (process, not design) |
| Quality & Design Standards (YAGNI) | No pattern/abstraction introduced without current need. Flood/rate-limiting was explicitly deferred (research.md §6) rather than speculatively built. | **PASS** |

No unjustified violations. One item is logged in Complexity Tracking below because three
storage backends for a two-entity data model could otherwise look like over-engineering — it is
justified there rather than silently accepted.

## Project Structure

### Documentation (this feature)

```text
specs/001-prompt-collection-bot/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md         # Phase 1 output (/speckit-plan command)
├── contracts/            # Phase 1 output (/speckit-plan command)
│   └── http-api.md
└── tasks.md              # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/
├── bot/                      # PromptSource port + TelegramPromptSource adapter
│   ├── ports.py
│   ├── telegram_adapter.py
│   └── handlers.py           # message routing (text / non-text / empty)
├── api/
│   ├── app.py                 # FastAPI app
│   ├── webhook.py             # POST /prompt
│   └── health.py               # GET /healthz
├── models/
│   ├── user.py
│   └── prompt.py
├── repositories/              # PromptRepository port + adapters
│   ├── ports.py
│   ├── postgres_repository.py
│   ├── minio_payload_store.py
│   └── in_memory_repository.py   # test fake
├── cache/                     # DedupCache port + adapters
│   ├── ports.py
│   ├── redis_cache.py
│   └── in_memory_cache.py        # test fake
├── services/
│   └── prompt_capture_service.py  # orchestrates capture, ack, dedup, retention
└── jobs/
    └── retention_cleanup.py       # daily 30-day expiry job

tests/
├── contract/        # FastAPI webhook contract tests (httpx.AsyncClient)
├── integration/      # real Postgres/Redis/MinIO via testcontainers
└── unit/              # handlers/services against in-memory fake adapters

docker/
├── Dockerfile
└── docker-compose.yml
```

**Structure Decision**: Single backend service (Option 1 pattern). No frontend/mobile
component exists or is implied by the spec, so the web-application (frontend+backend) and
mobile+API options are not applicable. `bot/`, `repositories/`, and `cache/` each hold a port
plus its adapters per the Ports-and-Adapters decision in research.md §9; `api/` is the FastAPI
webhook/health surface; `jobs/` holds the scheduled retention cleanup from research.md §4.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Three storage backends (PostgreSQL, MinIO, Redis) for a two-entity data model | The technology stack (MinIO, a SQL database, Redis) was specified as a fixed project-level constraint, not chosen speculatively for this feature. Each backend has a distinct, non-overlapping role: Postgres = queryable relational metadata; MinIO = durable raw-payload audit copy; Redis = ephemeral dedup cache (research.md §1, §3, §4). | A single-store alternative (Postgres only) was not adopted because it conflicts with the stack already committed to for the project, and would still need a separate idempotency mechanism (§3) and would store large raw payloads in the relational DB rather than object storage purpose-built for that. |
