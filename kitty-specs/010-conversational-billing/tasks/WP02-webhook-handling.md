---
work_package_id: "WP02"
subtasks:
  - "T010"
  - "T011"
  - "T012"
title: "Webhook Handling"
phase: "Phase 3 - Integration"
lane: "done"
dependencies: ["WP01"]
agent: "Antigravity"
shell_pid: "3779362"
review_status: "has_feedback"
reviewed_by: "MRiabov"
history:
  - timestamp: "2026-01-20T14:45:30Z"
    lane: "planned"
    agent: "antigravity"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 – Webhook Handling

## Objectives & Success Criteria

- Securely receive and process Stripe webhooks.
- Automatically update business records and entitlements upon successful payment.

## Context & Constraints

- Requires `WP01` for the `BillingService` integration.
- Must verify Stripe webhook signatures to prevent spoofing.
- Uses FastAPI endpoints.

## Subtasks & Detailed Guidance

### Subtask T010 – Create webhook endpoint

- **Purpose**: Receive events from Stripe.
- **Steps**:
  1. Create `src/api/webhooks/stripe_webhook.py` using FastAPI.
  2. Implement a POST route.
  3. Use `stripe.Webhook.construct_event` with `STRIPE_WEBHOOK_SECRET` for signature verification.
- **Files**: `src/api/webhooks/stripe_webhook.py`

### Subtask T011 – Implement webhook processing logic

- **Purpose**: Sync Stripe state to internal DB.
- **Steps**:
  1. Handle `checkout.session.completed` or `customer.subscription.updated`.
  2. Map Stripe metadata `business_id` back to internal records.
  3. Extract item quantities (seats) and active products (addons) from the subscription items.
  4. Update the `business` record in the database.
- **Files**: `src/services/billing_service.py`, `src/api/webhooks/stripe_webhook.py`

### Subtask T012 – Add integration tests

- **Purpose**: Verify end-to-end webhook flow.
- **Steps**:
  1. Create test cases that simulate Stripe payloads (using `webhook.json` contract).
  2. Verify that sending a valid payload to the endpoint results in DB updates for the target business.
- **Files**: `tests/integration/test_stripe_webhooks.py`

## Risks & Mitigations

- **Signature Failure**: Ensure the webhook secret is correctly configured and provided by Stripe.
- **Concurrency**: Handle potential race conditions if multiple webhooks arrive for the same entity.

## Definition of Done Checklist

- [x] Webhook endpoint implemented and functional
- [x] Signature verification working (tested with valid/invalid signatures)
- [x] DB updates correctly reflect Stripe subscription changes
- [x] Integration tests passing

## Review Guidance

- Pay close attention to the mapping between Stripe subscription items and the `active_addons` list.
- Verify that the webhook response is always 200 OK (if signature is valid) to prevent Stripe from retrying excessively.

## Activity Log

- 2026-01-20T14:45:30Z – antigravity – lane=planned – Prompt created.
- 2026-01-20T16:41:00Z – Antigravity – shell_pid=3779362 – lane=doing – Started implementation via workflow command
- 2026-01-20T16:50:29Z – Antigravity – shell_pid=3779362 – lane=for_review – Implemented Stripe webhook endpoint and processing logic. Added integration tests covering successful flow and error cases. Updated Business model with billing fields.
- 2026-01-20T16:51:57Z – Antigravity – shell_pid=3779362 – lane=doing – Started review via workflow command
- 2026-01-20T16:56:39Z – Antigravity – shell_pid=3779362 – lane=planned – Moved to planned
- 2026-01-20T17:23:35Z – Antigravity – shell_pid=3779362 – lane=doing – Started implementation via workflow command
- 2026-01-20T17:39:32Z – Antigravity – shell_pid=3779362 – lane=for_review – Implemented T010, T011, T012: Stripe webhook endpoint, verification logic, DB updates, and comprehensive integration tests.
- 2026-01-20T17:56:08Z – Antigravity – shell_pid=3779362 – lane=doing – Started review via workflow command
- 2026-01-20T17:58:00Z – Antigravity – shell_pid=3779362 – lane=done – Review passed: Verified webhook endpoint implementation with signature verification. Confirmed business logic updates subscription status, seats, and addons correctly based on stripe events. Integration tests pass.
