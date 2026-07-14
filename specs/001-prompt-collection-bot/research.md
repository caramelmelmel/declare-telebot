# Research: Telegram Prompt Collection

**Input stack constraint** (user-specified, fixed for this project): MinIO, python-telegram-bot,
FastAPI, Docker containers, a SQL database, Redis caching.

## 1. SQL database choice

- **Decision**: PostgreSQL.
- **Rationale**: "any SQL database" was left open by the stakeholder. PostgreSQL has first-class
  async driver support (asyncpg), mature Docker images, native support for `testcontainers` (needed
  for the constitution's test-first/integration-test discipline), and JSONB if semi-structured
  fields are ever needed. It is the most common default for a new containerized Python service.
- **Alternatives considered**: MySQL (equally viable, but weaker async-driver ecosystem in Python
  at present); SQLite (rejected — no safe concurrent-write story for a multi-instance/containerized
  service, unsuitable for anything beyond local scripts).

## 2. Telegram update delivery mode

- **Decision**: Telegram **webhook** delivery, received on a FastAPI endpoint
  (`POST /prompt`), which hands the parsed `Update` to python-telegram-bot's
  `Application.process_update()`.
- **Rationale**: Webhook mode fits a containerized, always-on "stable" service better than long
  polling — it avoids holding an outbound long-lived connection per instance, plays well with
  standard container health checks/load balancers, and is FastAPI's natural mode (HTTP in, HTTP
  ack out). It directly supports FR-005 (continuous availability) and SC-005 (fast recovery after
  restart), since a stateless webhook receiver needs no reconnect handshake to resume.
- **Alternatives considered**: Long polling via python-telegram-bot's built-in polling runner —
  simpler to run locally (no public HTTPS endpoint required) but does not fit a "stable",
  horizontally-restartable container service as cleanly, and duplicates the HTTP-serving role
  FastAPI already provides. Retained only as a documented local-dev convenience in quickstart.md,
  not as the production path.

## 3. Duplicate-delivery handling (idempotency)

- **Decision**: Two-layer idempotency: (a) Redis `SET NX` on the Telegram `update_id` with a 24h
  TTL, checked before any processing begins; (b) a DB-level unique constraint on
  `telegram_update_id` on the `Prompt` table as a backstop.
- **Rationale**: Telegram's webhook delivery is at-least-once — the same update can be redelivered
  if Telegram doesn't receive a timely 200 response. FR-006 requires no permanent loss, but
  redelivery must not create duplicate captured prompts or duplicate acknowledgment replies. Redis
  gives a fast, cheap check on the hot path; the DB constraint guarantees correctness even if the
  Redis check is ever bypassed or Redis data is evicted.
- **Alternatives considered**: DB unique constraint alone — rejected as the *sole* mechanism
  because it still allows duplicate work (e.g., a second outbound acknowledgment message) to happen
  before the DB write is attempted and fails.

## 4. 30-day retention / auto-expiry (FR-009, SC-006)

- **Decision**: A scheduled cleanup job (run on a daily interval) deletes `Prompt` rows where
  `received_at` is older than 30 days, and a MinIO bucket lifecycle rule expires the corresponding
  raw-payload objects after 30 days.
- **Rationale**: The durable stores (Postgres, MinIO) are what FR-009 governs — Redis is explicitly
  scoped to caching/dedup, not durable retention, so it is not part of the retention mechanism.
  Using MinIO's native bucket lifecycle policy avoids building custom object-expiry logic.
- **Alternatives considered**: Redis TTL for the primary record — rejected because captured
  prompts must survive restarts and remain queryable for their full 30-day life; Redis is not the
  durable store in this stack.

## 5. Non-text / empty message detection

- **Decision**: Use python-telegram-bot's built-in message filters (`filters.TEXT & ~filters.COMMAND`
  for valid prompts; explicit handlers for `filters.PHOTO`, `filters.Sticker.ALL`, `filters.VOICE`,
  `filters.Document.ALL`, etc., routed to a single "unsupported content" reply) plus a post-filter
  check that stripped text is non-empty (FR-008).
- **Rationale**: Library-native filtering avoids custom MIME/content-type sniffing and keeps the
  routing declarative and easy to test.
- **Alternatives considered**: Manually inspecting the raw `Update` payload for content type —
  rejected as unnecessary reimplementation of what the library already provides.

## 6. Message flooding / rapid succession (edge case)

- **Decision**: No additional custom rate limiter for this feature. FastAPI's async request
  handling processes each webhook call independently, and the Redis dedup layer (§3) already
  guards against duplicate processing; ordering is preserved by Telegram's per-chat update
  sequencing and DB insert order.
- **Rationale**: No functional requirement calls for throttling legitimate users, only for not
  dropping or merging their messages. Adding a token-bucket limiter now would be speculative
  complexity not justified by a current requirement (YAGNI, per the constitution's Quality &
  Design Standards).
- **Alternatives considered**: Per-user token-bucket in Redis — deferred; revisit only if abuse is
  observed in practice, at which point Redis already being in the stack makes it a cheap addition.

## 7. Testing strategy (Constitution Principle I — Test-First, NON-NEGOTIABLE)

- **Decision**: pytest + pytest-asyncio for unit tests against fake/in-memory adapters;
  `testcontainers-python` to spin up real ephemeral Postgres, Redis, and MinIO containers for
  integration tests exercising the real adapters; `httpx.AsyncClient` for FastAPI webhook contract
  tests; python-telegram-bot's test utilities (fake `Update`/`Bot` objects) for handler unit tests.
  Every handler, repository, and adapter is built test-first per the constitution.
- **Rationale**: Matches the constitution's non-negotiable TDD principle and the project's
  review-gated release principle (reviewers can verify tests existed first from commit history).
- **Alternatives considered**: Mocking Postgres/Redis/MinIO entirely in all tests — rejected as the
  sole strategy because it would not catch real integration issues (schema mismatches, driver
  quirks); real containers are used for the integration layer specifically to avoid that gap.

## 8. Containerization

- **Decision**: A multi-stage Dockerfile builds the Python service image; `docker-compose.yml`
  wires together the app, PostgreSQL, Redis, and MinIO for local development and CI.
- **Rationale**: Matches the user-specified stack directly and supports the constitution's
  review-gated production release workflow — a single built image is what gets reviewed/promoted.
- **Alternatives considered**: None — Docker was an explicit, non-negotiable stack requirement.

## 9. Extensibility pattern (Constitution Principle II — Pattern-Driven Extensibility)

- **Decision**: Ports-and-Adapters (Hexagonal). Define three ports (interfaces) with real and
  fake/in-memory adapters each:
  - `PromptSource` — real adapter: `TelegramPromptSource` (wraps python-telegram-bot); test
    adapter: an in-memory fake feeding synthetic `Update` objects.
  - `PromptRepository` — real adapter: `PostgresPromptRepository` (+ `MinioPayloadStore` for the
    raw-payload blob); test adapter: an in-memory fake repository.
  - `DedupCache` — real adapter: `RedisDedupCache`; test adapter: an in-memory fake cache.
- **Rationale**: The constitution requires at least two current or clearly planned use cases before
  introducing a pattern (no speculative abstraction). Each port here already has two concrete,
  present-day consumers — the real adapter (production) and the fake adapter (required by
  Principle I's test-first discipline, since handlers must be unit-testable without live
  Postgres/Redis/Telegram). This is not a bet on a hypothetical second messaging platform; it is
  driven by the testing requirement that already exists today.
- **Alternatives considered**: Direct, concrete calls to python-telegram-bot/SQLAlchemy/redis-py
  scattered through handler code — rejected because it would make test-first handler development
  impossible without hitting real external services for every unit test.
