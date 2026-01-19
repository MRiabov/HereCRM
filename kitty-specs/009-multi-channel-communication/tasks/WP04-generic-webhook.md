---
work_package_id: WP04
subtasks:
  - T015
  - T016
  - T017
lane: "doing"
agent: "Antigravity"
review_status: "has_feedback"
reviewed_by: "Antigravity"
history:
  - date: 2026-01-19
    action: created
---

## Review Feedback

**Status**: ❌ **Needs Changes**

**Key Issues**:

1. **Missing Rate Limiting**: Unlike the WhatsApp and Twilio webhooks, the `generic` webhook is missing a call to `check_rate_limit(payload.identity)`. This is a security and performance risk.
2. **Missing Authentication/Security**: The endpoint is currently public. While it's "generic", it should at least implement a basic API Key check (e.g., via a Header) to prevent unauthorized message injection and spam.
3. **Consistency**: Ensure the `channel` passed to `handle_message` for this endpoint is consistently "generic" or reflects the `payload.source`.

**What Was Done Well**:

- Good test coverage in `tests/test_generic_webhook.py`.
- Correct mapping logic for both email and phone identities.
- Proper Pydantic validation for the payload.

**Action Items**:

- [ ] Implement rate limiting using `check_rate_limit`.
- [ ] Add a basic API Key authentication check (use a setting like `GENERIC_WEBHOOK_SECRET`).
- [ ] Update tests to include the API Key header.

# WP04 - Generic Webhook Integration

## Objective

Create a generic endpoint for external systems to inject messages into the CRM.

## Context

Third-party tools (Zapier, Forms) need a way to create leads or send messages without using a specific channel provider like Twilio.

## Subtasks

### T015: Create Generic Webhook Endpoint

- Create `POST /webhooks/generic`.
- Define JSON Schema:

  ```json
  {
    "identity": "+1234567890", // or email
    "message": "Hello world",
    "source": "Zapier" // optional metadata
  }
  ```

- Implement validation.

### T016: Implement Mapping Logic

- Parse `identity`. Check if it looks like a phone number or email.
- Lookup `User` by that identity.
- Create `Message` entry.

### T017: Test Integration

- Create a simple test script or use `curl` to post data and verify it appears in the system.

## Test Strategy

- **Unit**: Test payload validation logic.
- **Integration**: Post data to the endpoint and check database for new Message.

## Activity Log

- 2026-01-19T18:48:28Z – Antigravity – lane=doing – Started implementation of Generic Webhook
- 2026-01-19T19:42:09Z – Antigravity – lane=for_review – Ready for review. Fixed ToolExecutor instantiation and verified generic webhook.
- 2026-01-19T19:53:00Z – Antigravity – lane=planned – Review complete: missing rate limiting and security checks.
- 2026-01-19T20:52:50Z – Antigravity – shell_pid= – lane=doing – Addressing review feedback: adding rate limiting and API key auth.
