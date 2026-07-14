# HTTP API Contract: Telegram Prompt Collection

The service exposes two HTTP endpoints via FastAPI. This is the only externally-facing
interface for this feature (all Telegram-facing behavior — acknowledgments, rejection
messages — is delivered back through the Telegram Bot API, not this HTTP surface, and is
covered by the acceptance scenarios in spec.md rather than a separate contract).

## POST /prompt

Receives Telegram Bot API `Update` payloads (webhook push delivery, research.md §2).

**Request**

- Header: `X-Telegram-Bot-Api-Secret-Token: <configured secret>` — required; requests missing
  or mismatching this header MUST be rejected before any processing.
- Body: a Telegram `Update` JSON object (as defined by the Telegram Bot API), any size within
  Telegram's own message limits.

**Behavior**

1. Validate the secret token header. Invalid/missing → `401 Unauthorized`, no processing.
2. Check the Redis dedup cache for `update.update_id` (research.md §3). If already seen →
   `200 OK` immediately, no further processing (idempotent no-op).
3. Otherwise, mark `update_id` as seen in Redis, then route by content:
   - Non-empty text, not a command → capture per FR-002/FR-004, persist `Prompt` (data-model.md)
     + raw payload to MinIO, reply to the user via the Telegram Bot API with a receipt
     acknowledgment (FR-003), respond `200 OK`.
   - Empty/whitespace-only text → do not persist a `Prompt`; reply via Telegram asking the user
     to send actual content (FR-008); respond `200 OK`.
   - Non-text content (photo/sticker/voice/document/etc.) → do not persist a `Prompt`; reply via
     Telegram explaining only text prompts are supported (FR-007); respond `200 OK`.
4. Any unexpected internal failure after step 1 → respond `200 OK` regardless (Telegram
   webhook convention: non-200 triggers Telegram's own retry/backoff, which combined with the
   dedup layer is acceptable, but a hung/5xx response risks Telegram temporarily disabling the
   webhook) and log the failure for operator visibility. This is an operational detail, not a
   user-facing behavior change.

**Response**

- `200 OK`, empty body — the standard Telegram webhook acknowledgment, in all reachable cases
  above once the secret token has validated.
- `401 Unauthorized` — secret token missing/invalid.

## GET /healthz

Operational liveness/readiness check for container orchestration (supports FR-005/SC-005 —
enables automatic detection that the service has resumed after a restart).

**Request**: none.

**Response**:
- `200 OK` with `{"status": "ok"}` when the process is up and its Postgres/Redis/MinIO
  connections are reachable.
- `503 Service Unavailable` with `{"status": "degraded", "detail": "<which dependency>"}` when
  any required dependency is not reachable.
