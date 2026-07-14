# Data Model: Telegram Prompt Collection

Derived from spec.md's Key Entities (User, Prompt) and Functional Requirements FR-002, FR-004,
FR-009. Two storage locations are involved per research.md: PostgreSQL holds the structured
records below; MinIO holds the raw payload blob referenced by `Prompt.raw_payload_object_key`.

## User

Represents a person interacting with the bot, identified by their Telegram account.

| Field | Type | Notes |
|---|---|---|
| `telegram_user_id` | bigint, PK | Telegram's unique numeric user ID. Never reused across users (FR-004, edge case: same display name). |
| `username` | text, nullable | Telegram `@username`, if the user has one set. Not unique/stable — display only. |
| `display_name` | text, nullable | Telegram first/last name at time of last message. Display only, never used for identity. |
| `first_seen_at` | timestamptz | Set once, on first captured prompt from this user. |
| `last_seen_at` | timestamptz | Updated on every captured prompt from this user. |

**Validation rules**:
- `telegram_user_id` is required and immutable once created.
- `username`/`display_name` may change on every message; always overwrite with the latest value (they are not identity, per FR-004 and the "same display name" edge case).

## Prompt

Represents a single captured text message ("prompt") sent by a user.

| Field | Type | Notes |
|---|---|---|
| `id` | UUID, PK | Internal identifier. |
| `user_id` | bigint, FK → `User.telegram_user_id` | Sender (FR-004). |
| `chat_id` | bigint | Telegram chat ID the message was sent in. For this feature always the 1:1 chat with the user (group chats out of scope). |
| `telegram_update_id` | bigint, unique | Telegram's update identifier; unique constraint backs the dedup mechanism (research.md §3). |
| `telegram_message_id` | bigint | Telegram's per-chat message identifier, for reference/troubleshooting. |
| `content` | text | The message text (FR-002). Never empty/whitespace-only — enforced before a row is created (FR-008). |
| `raw_payload_object_key` | text | Key of the corresponding raw-Update JSON object in MinIO (audit/recovery copy, research.md §9). |
| `received_at` | timestamptz | When the system captured the message (FR-002). |
| `expires_at` | timestamptz | `received_at + 30 days`, computed at insert time. Rows past this are removed by the retention job (FR-009, SC-006). |

**Validation rules**:
- `content` MUST be non-empty after trimming whitespace (FR-008) — messages failing this check are never persisted as a `Prompt`; the bot replies asking for real content instead (see contracts/http-api.md).
- `telegram_update_id` MUST be unique — a duplicate insert attempt (redelivery, research.md §3) is treated as already-captured and is a no-op, not an error surfaced to the user.
- `expires_at` MUST always equal `received_at + 30 days`; never set independently.

**Relationships**: One `User` has many `Prompt`s (1:N via `user_id`). No other relationships —
non-text/empty messages (User Story 3) are never persisted as a `Prompt` at all; they only
produce a reply to the user (no entity is created for them).

## Non-persisted concepts

- **Dedup marker** (Redis): `update_id → 1`, TTL 24h. Not a durable entity — purely an
  ephemeral guard checked before processing (research.md §3); has no relational fields.
- **Rejected input** (non-text or empty message, User Story 3): intentionally has no data
  model — it produces only a reply to the user, per FR-007/FR-008. If future analytics on
  rejected input become a requirement, that would be a new, separate feature.

## State / lifecycle

`Prompt` rows are append-only and immutable after creation, with exactly one transition:
**captured → expired (deleted)** at `expires_at`, performed by the retention cleanup job
(research.md §4). There is no update path — a resent/edited message on Telegram arrives as a
new `Update`/`telegram_update_id` and becomes a new, distinct `Prompt` row (spec.md Acceptance
Scenario: "without overwriting or losing the earlier one").
