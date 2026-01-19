---
work_package_id: WP03
subtasks:
  - T011
  - T012
  - T013
  - T014
lane: planned
history:
  - date: 2026-01-19
    action: created
---

# WP03 - Email Channel Support (Postmark)

## Objective

Implement Email sending and receiving capabilities using Postmark.

## Context

Email allows for richer, longer-form communication. We use Postmark for transactional email reliability.

## Subtasks

### T011: Implement PostmarkService

- Create `src/services/postmark_service.py`.
- Methods: `send_email(to_email: str, subject: str, body: str)`.
- Env vars: `POSTMARK_SERVER_TOKEN`, `FROM_EMAIL_ADDRESS`.

### T012: Implement Inbound Webhook

- Create endpoint: `POST /webhooks/postmark/inbound`.
- Parse JSON payload from Postmark (Inbound Webhook format).
- Extract `From`, `Subject`, `TextBody`.

### T013: Link Inbound Email to User

- Logic: Find `User` where `email` matches `From`.
- If not found, create new user with this email (if allowed).

### T014: Handle Threading

- Extract `Message-ID`, `In-Reply-To`, `References` headers.
- Store these in `Message` metadata if necessary to maintain conversation threads in standard clients.
- When sending replies, ensure `In-Reply-To` is set if replying to a specific message thread (optional for MVP, but good for UX).

## Test Strategy

- **Unit**: Mock Postmark client.
- **Integration**: Simulate Postmark JSON payload to the webhook endpoint.
- **Validation**: Verify headers are parsed correctly.
