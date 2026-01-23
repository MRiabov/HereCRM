---
work_package_id: "WP05"
subtasks:
  - "T020"
  - "T021"
  - "T022"
  - "T023"
  - "T024"
title: "Usage-Based Billing"
phase: "Phase 5 - Security & Monetization"
lane: "done"
dependencies: ["WP00", "WP01", "WP02", "WP03", "WP04"]
agent: "Antigravity"
shell_pid: "164053"
reviewed_by: "MRiabov"
review_status: "approved"
history:
  - timestamp: "2026-01-21T08:30:00Z"
    lane: "planned"
    agent: "antigravity"
    action: "Prompt manually generated for WP05"
---

# Work Package Prompt: WP05 – Usage-Based Billing

## Objectives & Success Criteria

- Implement usage-based billing for messaging (with extra cost per message).
- Track message usage per billing period.
- Report usage to Stripe (Metered Billing) or calculate locally and add to invoice.
- Display usage stats to users.

## Context & Constraints

- Integrates with `BillingService` and `WhatsAppService`.
- Uses Stripe Metered Billing (or invoice items).
- Requires modification of the `Business` model to track `message_count_current_period`.

## Subtasks & Detailed Guidance

### Subtask T020 – Update Business model

- **Purpose**: Store usage counters and cycle info.
- **Steps**:
  1. Add `message_count_current_period` (int, default 0) to `Business` model.
  2. Add `billing_cycle_anchor` (datetime, nullable) to `Business` model (to know when to reset count).
  3. Add `message_credits` (int, default 0) to `Business` model (for credit balance).
  4. Generate and run Alembic migration.
- **Files**: `src/models.py`, `src/repositories.py` (if needed)

### Subtask T021 – Update BillingService for usage tracking

- **Purpose**: Track messages and handle Stripe logic.
- **Steps**:
  1. Implement `track_message_sent(business_id)`.
     - Decrement `message_credits`.
     - Increment `message_count_current_period`.
     - If `message_credits` < 0, calculate overage and report to Stripe or track.
  2. Ensure `process_webhook_event` handles cycle reset (`invoice.created`) to:
     - Reset `message_count_current_period`.
     - Add 1000 credits to `message_credits`.
- **Files**: `src/services/billing_service.py`

### Subtask T022 – Update billing status display

- **Purpose**: Show users their consumption.
- **Steps**:
  1. Update `get_billing_status` to include "Messages: X/1000".
  2. Calculate and show estimated overage cost if X > 1000.
- **Files**: `src/services/billing_service.py`, `src/assets/messages.yaml` (if templates need update)

### Subtask T023 – Connect WhatsAppService

- **Purpose**: Count every sent message.
- **Steps**:
  1. Inject `BillingService` into `WhatsAppService`.
  2. Call `track_message_sent` for every outbound user message.
- **Files**: `src/services/whatsapp_service.py`

### Subtask T024 – Verify with tests

- **Purpose**: Ensure accurate billing.
- **Steps**:
  1. Create `tests/test_usage_billing.py`.
  2. specific tests for:
     - Incrementing count.
     - Resetting count on cycle end (mock webhook).
     - Cost calculation logic.
- **Files**: `tests/test_usage_billing.py`

### Subtask T025 – Implement Messaging Top-up

- **Purpose**: Allow users to buy credits.
- **Steps**:
  1. Update `RequestUpgradeTool` to accept "messaging".
  2. Update `BillingService.create_upgrade_link` to support one-time payment mode.
  3. Handle `checkout.session.completed` (payment mode) to add credits.
- **Files**: `src/uimodels.py`, `src/services/billing_service.py`

## Risks & Mitigations

- **Double counting**: Ensure retries don't double count (idempotency).
- **Performance**: DB write on every message? Just incrementing an integer is fast, but be mindful.
- **Stripe Sync**: If Stripe request fails, do we fail sending message? No, should be async or best effort/background.

## Definition of Done Checklist

- [x] **T020**: Update `Business` model to include `message_count_current_period` (int), `billing_cycle_anchor` (datetime), and `message_credits` (int). <!-- id: 19 -->
- [x] **T021**: Update `BillingService` to support usage tracking: `track_message_sent` decrements credits, reports overage if negative. Reset logic adds 1000 credits/month. <!-- id: 20 -->
- [x] **T022**: Update `get_billing_status` to formatting to include "X credits remaining" or "Overage: Y". <!-- id: 21 -->
- [x] **T023**: Connect `WhatsAppService` (or message sender) to `BillingService.track_message_sent` to increment usage on every outbound message. <!-- id: 22 -->
- [x] **T024**: Verify usage tracking and cost calculation with new tests in `tests/test_usage_billing.py` and `tests/test_billing_fixes.py`. <!-- id: 23 -->
- [x] **T025**: Implement messaging top-up flow and payment handling. <!-- id: 24 -->

## Review Guidance

- Check that the first 1000 messages are indeed free.
- Verify that the overage rate is correct ($0.02).
- Ensure DB migration is clean.

## Activity Log

- 2026-01-21T09:33:32Z – antigravity – shell_pid=3980068 – lane=doing – Started implementation via workflow command
- 2026-01-22T11:13:21Z – antigravity – shell_pid=3980068 – lane=for_review – Implemented usage-based billing with Stripe metered billing. Added usage tracking to WhatsappService and BillingService. Updated conversational UI to display usage statistics. Verified with tests.
- 2026-01-22T11:14:36Z – Antigravity – shell_pid=164053 – lane=doing – Started review via workflow command
- 2026-01-22T11:16:05Z – Antigravity – shell_pid=164053 – lane=done – Review passed: Implementation verified, tests passed, code meets requirements.
