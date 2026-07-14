# Feature Specification: Telegram Prompt Collection

**Feature Branch**: `001-prompt-collection-bot`

**Created**: 2026-07-13

**Status**: Draft

**Input**: User description: "Create a python telegram bot application that uses a stable telegram bot to collect the user's prompt when the user chats with the telegram bot."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Send a message and have it captured (Priority: P1)

A user opens a direct chat with the bot on Telegram and sends a text message (their
"prompt"). The system reliably receives that message, records who sent it and when, and
confirms to the user that it was received.

**Why this priority**: This is the foundational capability of the whole product — without
reliable message capture, no downstream feature (search, Q&A, devotionals, etc.) can exist.
It is the smallest possible slice that delivers standalone value: a working, responsive bot.

**Independent Test**: Can be fully tested by messaging the bot from a Telegram account and
verifying (a) the bot replies with an acknowledgment, and (b) the message is retrievable
afterward (e.g., in storage/logs) with the correct sender and timestamp.

**Acceptance Scenarios**:

1. **Given** a user has opened a chat with the bot for the first time, **When** they send a
   text message, **Then** the system captures the message content, sender identity, and
   timestamp, and the bot replies with a receipt confirmation.
2. **Given** a user has previously messaged the bot, **When** they send another message,
   **Then** the new message is captured as a distinct entry linked to the same user, without
   overwriting or losing the earlier one.

---

### User Story 2 - Bot stays available and recovers from disruptions (Priority: P2)

The bot continues to accept and capture messages reliably over time, including recovering
automatically after a restart, deployment, or brief network/service interruption, without
requiring manual intervention and without permanently losing messages sent during the gap.

**Why this priority**: A bot that silently drops messages during outages undermines trust in
the entire system ("stable" was an explicit requirement). This builds directly on User Story
1's capture pipeline by making it durable.

**Independent Test**: Can be fully tested by sending a message, restarting the running bot
process, and confirming that (a) the bot resumes accepting new messages automatically, and
(b) any messages sent by users while the bot was offline are still captured once it comes
back online (per Telegram's own message-delivery guarantees).

**Acceptance Scenarios**:

1. **Given** the bot process is stopped and restarted, **When** a user sends a message after
   restart, **Then** the bot captures it and replies normally within the same time bounds as
   before the restart.
2. **Given** the bot was briefly unreachable while a user sent a message, **When** the bot
   comes back online, **Then** it processes and captures the message that was queued for
   delivery, rather than silently discarding it.

---

### User Story 3 - Graceful handling of non-text input (Priority: P3)

A user sends something other than plain text (a photo, sticker, voice note or an
empty/whitespace-only message). The bot recognizes it cannot capture it as a prompt and tells
the user clearly what is supported, instead of failing silently or crashing.

**Why this priority**: Improves user experience and system robustness once the core text
capture path (P1) and durability (P2) are in place, but the product remains viable without it
in the very first release.

**Independent Test**: Can be fully tested by sending a photo or sticker to the bot and
confirming it responds with a clear "text only" message rather than erroring or ignoring the
input.

**Acceptance Scenarios**:

1. **Given** a user sends a photo, sticker, voice note, or other non-text content, **When**
   the bot receives it, **Then** it replies explaining that only text prompts are supported
   and does not record it as a captured prompt.
2. **Given** a user sends an empty or whitespace-only message, **When** the bot receives it,
   **Then** it asks the user to send an actual message instead of capturing a blank prompt.

---

### User Story 4 - Daily chat session (Priority: P3)

A user sends a message the next day at 8am, the system will start a new session for the user. The bot will reply to the user when a message starts the next day

**Why this priority**: Improves the user experience and makes the user feel acknowledged that the message has been received in the system.

**Independent Test**: Can be fully tested by sending a message to the bot, and then
manually replaying the same update payload (using the update ID) to the webhook endpoint.
Verify that the bot acknowledges the message only once and that only one prompt record is
created in the database.

**Acceptance Scenarios**:

1. **Given** a user sends a message at 7:59am on day 1, **When** they send another message at 8:01am on day 2, **Then** the system starts a new session for the user and the bot replies to the user.

2. **Given** a user sends a message at 7:59am on day 1, **When** they send another message at 7:59am on day 2, **Then** the system does not start a new session for the user and the bot replies to the user.

3. **Given** a user sends a message at 7:59am on day 1, **When** they send another message at 7:59am on day 1, **Then** the system does not start a new session for the user and the bot replies to the user.

4. **Given** the user sends a message at 8:01am on day 1, **When** they send another message at 7:59am on day 2, **Then** the system does not start a new session for the user and the bot replies to the user.

---

### Edge Cases

- What happens when a user sends an extremely long message (beyond Telegram's own message
  size limit)? The bot MUST still capture as much as Telegram delivers and must not crash.
- What happens when the same user sends multiple messages in rapid succession (message
  flooding)? Every distinct message MUST still be captured in order, without being dropped
  or merged.
- What happens when a user blocks the bot or deletes their chat after sending a message? The
  already-captured message MUST remain intact; only future delivery to that user is affected.
- What happens when a message is sent inside a group chat the bot is a member of, rather than
  a direct 1:1 chat? (See Assumptions — group chats are out of scope for this feature.)
- How does the system handle two users with the same display name? Users MUST be
  distinguished by their unique Telegram account identity, not by display name.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST allow any user to start a direct (1:1) chat with the bot on
  Telegram and send a text message to it.
- **FR-002**: The system MUST capture every text message a user sends, recording at minimum:
  the message content, the sender's unique account identity, and the time it was received.
- **FR-003**: The system MUST reply to the user with an acknowledgment after successfully
  capturing their message, so the user knows it was received.
- **FR-004**: The system MUST associate every captured message with the sending user's
  unique Telegram identity, so messages from different users are never conflated and repeat
  messages from the same user are recognized as belonging to that user.
- **FR-005**: The system MUST remain continuously available to receive messages, and MUST
  automatically resume accepting messages after a restart or transient failure without manual
  intervention.
- **FR-006**: The system MUST NOT permanently lose a message that a user sent while the
  system was briefly unavailable, provided Telegram itself still has that message queued for
  delivery.
- **FR-007**: The system MUST detect when an incoming message is not plain text (photo,
  sticker, voice note, document, etc.) and respond to the user explaining that only text
  prompts are currently supported, without treating the non-text input as a captured prompt.
- **FR-008**: The system MUST detect empty or whitespace-only text messages and prompt the
  user to send actual content instead of capturing a blank entry.
- **FR-009**: The system MUST retain each captured prompt in a durable store for 30 days on
  a rolling basis from the time it was captured, after which it MUST be automatically
  expired/removed.
- **FR-010**: The system MUST limit its response to each captured message to a plain receipt
  acknowledgment only; it MUST NOT generate or send substantive answer content in this
  feature. Generating an actual reply/answer to the user's prompt (e.g., a Bible-related
  response) is explicitly out of scope for this feature and will be delivered by a separate,
  later feature.

### Key Entities *(include if feature involves data)*

- **User**: A person interacting with the bot, identified by their unique Telegram account
  identity. Attributes of interest: unique identifier, display name/username (if available).
- **Prompt**: A single text message a user sends to the bot. Attributes: message content,
  the User who sent it, the chat it was sent in, and the timestamp it was received.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 99% of text messages sent to the bot receive an acknowledgment reply within 3
  seconds under normal operating conditions.
- **SC-002**: Zero captured prompts are lost or corrupted across a simulated bot restart
  during active use.
- **SC-003**: 100% of non-text messages (photos, stickers, voice notes) receive a clear
  "text only" explanation rather than being silently ignored or causing an error.
- **SC-004**: The system correctly attributes 100% of captured prompts to the correct
  sending user, verified across at least 50 messages from multiple distinct users.
- **SC-005**: The bot recovers from an unplanned restart and resumes accepting messages
  within 1 minute, with no manual intervention required.
- **SC-006**: Captured prompts older than 30 days are automatically no longer retrievable,
  verified by checking that no prompt older than 30 days remains in storage.

## Assumptions

- Only direct (1:1) chats between a user and the bot are in scope for this feature; handling
  the bot being added to group chats is out of scope until a future feature.
- "Stable" is interpreted as: continuous availability plus automatic recovery from restarts
  and transient failures, per User Story 2 and FR-005/FR-006, rather than any specific
  numeric uptime SLA.
- Prompts are plain text only for this feature; interpreting or transcribing non-text content
  (images, voice) is out of scope and instead handled per FR-007 (graceful rejection).
- No user authentication beyond Telegram's own account identity is required — a user's
  Telegram account ID is sufficient to identify them.
- This feature covers capture and acknowledgment only; any feature that generates a
  substantive reply to the captured prompt (e.g., answering a Bible question) is a separate,
  future feature built on top of this one.
