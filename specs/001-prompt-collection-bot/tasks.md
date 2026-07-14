---

description: "Task list template for feature implementation"
---

# Tasks: Telegram Prompt Collection

**Input**: Design documents from `/specs/001-prompt-collection-bot/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/http-api.md, quickstart.md

**Tests**: Included and REQUIRED — the project constitution (`.specify/memory/constitution.md`,
Principle I, NON-NEGOTIABLE) mandates test-first development for every change; tests are not
optional for this project and must be written and failing before their implementation task.

**Organization**: Tasks are grouped by user story (from spec.md) to enable independent
implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Paths follow the single-project layout from plan.md (`src/`, `tests/`, `docker/` at repo root)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create project structure per plan.md (`src/{bot,api,models,repositories,cache,services,jobs}/`, `tests/{contract,integration,unit}/`, `docker/`)
- [X] T002 Initialize Python 3.12 project in `pyproject.toml` with dependencies: fastapi, python-telegram-bot, sqlalchemy[asyncio], asyncpg, alembic, redis, minio, pytest, pytest-asyncio, testcontainers, httpx
- [X] T003 [P] Configure linting and formatting (ruff + black) in `pyproject.toml`
- [X] T004 [P] Create `docker/Dockerfile` (multi-stage build) for the app image
- [X] T005 [P] Create `docker/docker-compose.yml` wiring app, postgres, redis, minio for local dev/CI
- [X] T006 [P] Create `.env.example` with `TELEGRAM_BOT_TOKEN`, Postgres/Redis/MinIO connection settings, and webhook secret token

**Checkpoint**: Project skeleton and local stack are runnable (`docker compose up`).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T007 Implement application configuration loader (env vars) in `src/config.py`
- [X] T008 Setup Alembic migrations framework and async SQLAlchemy engine/session in `src/db/session.py` (depends on T002)
- [X] T009 [P] Define `PromptSource` port (interface) in `src/bot/ports.py`
- [X] T010 [P] Define `PromptRepository` port (interface, covering both relational + raw-payload storage) in `src/repositories/ports.py`
- [X] T011 [P] Define `DedupCache` port (interface) in `src/cache/ports.py`
- [X] T012 [P] Implement in-memory fake `PromptRepository` test adapter in `src/repositories/in_memory_repository.py` (depends on T010)
- [X] T013 [P] Implement in-memory fake `DedupCache` test adapter in `src/cache/in_memory_cache.py` (depends on T011)
- [X] T014 [P] Create `User` ORM model + Alembic migration in `src/models/user.py` (depends on T008)
- [X] T015 Create `Prompt` ORM model (unique `telegram_update_id` constraint, `expires_at` field per data-model.md) + Alembic migration in `src/models/prompt.py` (depends on T008, T014)
- [X] T016 Implement FastAPI app skeleton with dependency-injected adapters in `src/api/app.py` (depends on T009, T010, T011)
- [X] T017 [P] Implement `GET /healthz` endpoint checking Postgres/Redis/MinIO connectivity per contracts/http-api.md in `src/api/health.py` (depends on T016)
- [X] T018 Implement `POST /prompt` route skeleton — secret-token validation (`401` on mismatch) and Update parsing, with a pluggable dispatch point for handlers — in `src/api/webhook.py` (depends on T016)
- [X] T019 [P] Implement `TelegramPromptSource` adapter wrapping python-telegram-bot Update processing in `src/bot/telegram_adapter.py` (depends on T009)

**Checkpoint**: Foundation ready - user story implementation can now begin.

---

## Phase 3: User Story 1 - Send a message and have it captured (Priority: P1) 🎯 MVP

**Goal**: A user sends a text message in a direct chat; the system captures content, sender,
and timestamp, persists it durably, and replies with a receipt acknowledgment.

**Independent Test**: Message the bot from a Telegram account; verify the bot replies with an
acknowledgment and the message is retrievable afterward with the correct sender and timestamp.

### Tests for User Story 1 ⚠️

> **Write these tests FIRST and confirm they FAIL before implementation (Constitution Principle I)**

- [X] T020 [P] [US1] Contract test: `POST /prompt` with a valid text message returns `200` and triggers an acknowledgment send, in `tests/contract/test_webhook_text.py`
- [ ] T021 [P] [US1] ~~Integration test~~ **DEFERRED — no Docker daemon in this environment; testcontainers cannot run.** Coverage for capture→Postgres/MinIO is instead provided via T020 (contract test) and T022 (unit test) against fake adapters. Revisit with real Postgres/MinIO once Docker is available, in `tests/integration/test_capture_prompt.py`
- [X] T022 [P] [US1] Unit test: `PromptCaptureService.capture()` persists via the fake repository and triggers an acknowledgment, in `tests/unit/test_prompt_capture_service.py`

### Implementation for User Story 1

- [X] T023 [P] [US1] Implement `PostgresPromptRepository`: save `Prompt`, upsert `User` (create on first message, update `last_seen_at`/`username`/`display_name` on each), compute `expires_at`, in `src/repositories/postgres_repository.py` (depends on T014, T015, T010)
- [X] T024 [P] [US1] Implement `MinioPayloadStore` adapter: store raw Update JSON, return object key, in `src/repositories/minio_payload_store.py` (depends on T010)
- [X] T025 [US1] Implement `PromptCaptureService` orchestrating persistence, raw payload storage, and acknowledgment dispatch, in `src/services/prompt_capture_service.py` (depends on T023, T024)
- [X] T026 [US1] Implement text-message handler in `src/bot/handlers.py` routing non-empty text to `PromptCaptureService` and sending the receipt acknowledgment (depends on T025, T019)
- [X] T027 [US1] Wire the text handler into `POST /prompt` in `src/api/webhook.py` (depends on T018, T026)
- [X] T028 [US1] Add structured logging for the capture lifecycle (received/persisted/acknowledged) in `src/services/prompt_capture_service.py` (depends on T025)

**Checkpoint**: User Story 1 (MVP) is fully functional and independently testable.

---

## Phase 4: User Story 2 - Bot stays available and recovers from disruptions (Priority: P2)

**Goal**: The bot keeps accepting messages reliably over time, recovers automatically after a
restart or brief outage, and never double-processes or permanently loses a redelivered message.

**Independent Test**: Send a message, restart the bot process, confirm it resumes accepting
messages automatically, and confirm a message sent during a brief outage is still captured
(not silently discarded, not duplicated) once the bot is back online.

### Tests for User Story 2 ⚠️

> **Write these tests FIRST and confirm they FAIL before implementation (Constitution Principle I)**

- [X] T029 [P] [US2] ~~Integration test (testcontainers)~~ **ADAPTED — no Docker daemon in this environment.** Implemented instead as a contract test driving `POST /prompt` twice with the same `update_id` against fake adapters, asserting only one `Prompt` is captured and only one acknowledgment is sent, in `tests/contract/test_webhook_dedup.py`
- [X] T030 [P] [US2] Unit test: the fake `DedupCache` marks an `update_id` as seen and short-circuits reprocessing, in `tests/unit/test_dedup_cache.py`
- [ ] T031 [P] [US2] Integration test: the service resumes capturing messages within the recovery window after a simulated restart. **DEFERRED — requires a real running process/container to restart; no Docker daemon in this environment.** Revisit once Docker/CI is available, in `tests/integration/test_restart_recovery.py`

### Implementation for User Story 2

- [X] T032 [P] [US2] Implement `RedisDedupCache` adapter (`SET NX` with 24h TTL) in `src/cache/redis_cache.py` (depends on T011)
- [X] T033 [US2] Integrate the dedup check into `POST /prompt`: short-circuit with `200 OK` on an already-seen `update_id` before dispatch, in `src/api/webhook.py` (depends on T032, T027)
- [X] T034 [US2] Handle a duplicate `telegram_update_id` DB constraint violation as a no-op rather than an error (dedup backstop), in `src/repositories/postgres_repository.py` (depends on T023) — done as part of T023

**Checkpoint**: User Stories 1 AND 2 both work independently.

---

## Phase 5: User Story 3 - Graceful handling of non-text input (Priority: P3)

**Goal**: A user who sends a photo, sticker, voice note, document, or an empty/whitespace-only
message gets a clear explanation instead of the input being silently ignored, captured as a
blank prompt, or causing an error.

**Independent Test**: Send a photo or sticker to the bot and confirm it replies with a clear
"text only" message rather than erroring or ignoring the input; send a blank message and
confirm it asks for real content.

### Tests for User Story 3 ⚠️

> **Write these tests FIRST and confirm they FAIL before implementation (Constitution Principle I)**

- [X] T035 [P] [US3] Contract test: `POST /prompt` with a photo/sticker payload returns `200`, triggers a rejection reply, and persists no `Prompt`, in `tests/contract/test_webhook_nontext.py`
- [X] T036 [P] [US3] Contract test: `POST /prompt` with empty/whitespace-only text returns `200`, triggers a rejection reply, and persists no `Prompt`, in `tests/contract/test_webhook_empty.py`
- [X] T037 [P] [US3] Unit test: handlers route non-text content types and empty text to the correct rejection reply, in `tests/unit/test_handlers_rejection.py`

### Implementation for User Story 3

- [X] T038 [US3] Implement non-text content handlers (photo/sticker/voice/document filters) replying with a "text only" explanation, in `src/bot/handlers.py` (depends on T026)
- [X] T039 [US3] Implement empty/whitespace-only text detection and a prompt-for-content reply, in `src/bot/handlers.py` (depends on T026)
- [X] T040 [US3] Wire the non-text and empty-text handlers into `POST /prompt` in `src/api/webhook.py` (depends on T027, T038, T039)

**Checkpoint**: All three user stories are independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Retention (FR-009/SC-006), operational hardening, and final validation across all stories

- [X] T041 [P] ~~Integration test (testcontainers)~~ **ADAPTED — no Docker daemon in this environment.** Implemented instead as a unit test seeding a 31-day-old `Prompt` into the fake repository/payload-store, running the job, and asserting the row + payload are removed while a fresher row is untouched, in `tests/unit/test_retention_cleanup.py`
- [X] T042 Implement `retention_cleanup` job (delete expired `Prompt` rows from Postgres and their corresponding MinIO objects) in `src/jobs/retention_cleanup.py` (depends on T041, T023, T024)
- [X] T043 [P] Configure a MinIO bucket lifecycle rule (30-day object expiry, via `MinioPayloadStore._ensure_lifecycle_rule`) and daily scheduling of `retention_cleanup` (via the `retention-cleanup` service `--loop --interval-seconds 86400`) in `docker/docker-compose.yml`
- [X] T044 [P] Contract test for `GET /healthz` degraded-dependency response, in `tests/contract/test_health.py`
- [X] T045 [P] Add `README.md` with setup/run instructions referencing quickstart.md
- [X] T046 Security hardening: constant-time secret-token comparison (`hmac.compare_digest`) in `POST /prompt`, no raw message content logged, unexpected dispatch failures caught and logged rather than propagating a non-200, in `src/api/webhook.py`
- [ ] T047 ~~Run quickstart.md validation end-to-end~~ **PARTIAL — no Docker/real Telegram bot token in this environment.** Substituted with: full automated test suite (18 tests) green, plus a manual ASGI-transport smoke test exercising `GET /healthz` and `POST /prompt`. Full docker-compose + real-bot quickstart run still needs to happen where Docker is available (see README "Known gaps").

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational completion - no dependency on other stories
- **User Story 2 (Phase 4)**: Depends on Foundational completion; its webhook integration (T033) builds on US1's route (T027), so implement after US1 in practice even though its dedup adapter (T032) could start earlier
- **User Story 3 (Phase 5)**: Depends on Foundational completion; its handler wiring (T038-T040) builds on US1's handler module (T026) and route (T027)
- **Polish (Phase 6)**: Depends on US1's repository/payload-store adapters (T023, T024) for the retention job

### User Story Dependencies

- **User Story 1 (P1)**: No dependencies on other stories — pure MVP slice
- **User Story 2 (P2)**: Independently testable per spec.md, but its implementation tasks touch the same `src/api/webhook.py` file US1 creates, so sequence after US1 in single-developer execution
- **User Story 3 (P3)**: Independently testable per spec.md, but its implementation tasks touch the same `src/bot/handlers.py` and `src/api/webhook.py` files US1 creates, so sequence after US1 in single-developer execution

### Within Each User Story

- Tests MUST be written and FAIL before implementation (Constitution Principle I, NON-NEGOTIABLE)
- Repository/adapter tasks before service tasks
- Service tasks before handler/route wiring
- Story complete (checkpoint) before moving to the next priority

### Parallel Opportunities

- All Setup tasks marked [P] (T003-T006) can run in parallel
- Foundational port definitions (T009-T011) and their fakes (T012-T013) can run in parallel; the User/Prompt models (T014) can run in parallel with the ports
- All tests within a user story marked [P] can run in parallel
- T023 and T024 (repository and payload-store adapters) can run in parallel within US1
- Different user stories could be worked on in parallel by different developers once Foundational is done, provided they coordinate on the shared files noted above (`webhook.py`, `handlers.py`)

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Contract test for POST /prompt text happy path in tests/contract/test_webhook_text.py"
Task: "Integration test for text message capture in tests/integration/test_capture_prompt.py"
Task: "Unit test for PromptCaptureService in tests/unit/test_prompt_capture_service.py"

# Launch independent adapter implementations for User Story 1 together:
Task: "Implement PostgresPromptRepository in src/repositories/postgres_repository.py"
Task: "Implement MinioPayloadStore adapter in src/repositories/minio_payload_store.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: run the User Story 1 section of quickstart.md
5. Deploy/demo if ready — this alone satisfies the core ask ("collect the user's prompt")

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → validate independently → Deploy/Demo (MVP!)
3. Add User Story 2 → validate independently (restart + redelivery scenarios) → Deploy/Demo
4. Add User Story 3 → validate independently (non-text/empty scenarios) → Deploy/Demo
5. Phase 6 polish (retention, hardening) → final quickstart.md run

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1
   - Developer B: User Story 2 (dedup adapter T032 can start immediately; webhook integration T033 waits on US1's T027)
   - Developer C: User Story 3 (handler tests can start immediately; wiring T038-T040 waits on US1's T026/T027)
3. Coordinate on shared files (`src/api/webhook.py`, `src/bot/handlers.py`) to avoid merge conflicts

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Tests are mandatory per the project constitution — verify each fails before implementing
- Commit after each task or logical group; every merge requires review + explicit approval before production deploy (Constitution Principle III)
- Stop at any checkpoint to validate a story independently
- Avoid: vague tasks, same-file conflicts without coordination, cross-story dependencies that break independence
