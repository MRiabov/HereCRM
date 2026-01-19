---
work_package_id: WP03
subtasks:
  - T011
  - T012
  - T013
  - T014
lane: planned
review_status: has_feedback
reviewed_by: Antigravity
history:
  - date: 2026-01-19
    action: created
  - date: 2026-01-19
    action: started_implementation
    agent: codex
  - date: 2026-01-19
    action: completed_implementation
    agent: codex
  - date: 2026-01-19
    action: review_feedback
    agent: Antigravity
    lane: planned
    status: needs_changes
---

## Review Feedback

**Status**: ❌ **Needs Changes**

**Key Issues**:

1. **Missing Implementation in Worktree**: The codebase in this worktree (`.worktrees/009-multi-channel-communication`) does not contain *any* of the required implementations for WP03. Specifically, `src/services/postmark_service.py` is missing.
2. **Suspected Misplaced Files**: Metadata suggests you might be working on files like `tests/test_postmark_webhook.py` in the root workspace (`/home/maksym/Work/proj/HereCRM`) instead of this worktree. Please move your changes to this feature branch and worktree.
3. **No Tests Found**: No Postmark-related tests were found in the `tests` directory of this worktree.

**Action Items** (must complete before re-review):

- [ ] Move `src/services/postmark_service.py` and any other implementation files to `.worktrees/009-multi-channel-communication`.
- [ ] Move any new tests to `.worktrees/009-multi-channel-communication/tests`.
- [ ] Ensure all changes are committed to the `009-multi-channel-communication` branch.
- [ ] Run tests in this worktree to verify they pass.

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
