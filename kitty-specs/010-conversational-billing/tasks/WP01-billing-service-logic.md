---
work_package_id: "WP01"
subtasks:
  - "T006"
  - "T007"
  - "T008"
  - "T009"
title: "Billing Service Logic"
phase: "Phase 2 - Core Services"
lane: "doing"
dependencies: ["WP00"]
agent: "Antigravity"
shell_pid: "3779362"
history:
  - timestamp: "2026-01-20T14:45:30Z"
    lane: "planned"
    agent: "antigravity"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – Billing Service Logic

## Objectives & Success Criteria

- Implement the core business logic for subscription management via Stripe.
- Provide a reliable interface for checking billing status and generating payment links.

## Context & Constraints

- Requires `WP00` for dependencies and data models.
- Uses the `stripe` python SDK.
- Must handle Stripe API errors gracefully.

## Subtasks & Detailed Guidance

### Subtask T006 – Create BillingService skeleton

- **Purpose**: Establish the service class and configuration.
- **Steps**:
  1. Create `src/services/billing_service.py`.
  2. Implement `BillingService` class.
  3. Initialize `stripe.api_key` from `STRIPE_SECRET_KEY` environment variable.
- **Files**: `src/services/billing_service.py`

### Subtask T007 – Implement get_billing_status

- **Purpose**: Fetch formatted subscription info for a business.
- **Steps**:
  1. Method `async def get_billing_status(self, business_id: int) -> dict`.
  2. Query DB via `BusinessRepository` for subscription fields.
  3. Return a dictionary containing user-friendly plan name, seat usage/limit, and active addons list.
- **Files**: `src/services/billing_service.py`

### Subtask T008 – Implement payment link generation

- **Purpose**: Create Stripe Checkout sessions for upgrades.
- **Steps**:
  1. `async def create_checkout_session(...)` for new subscriptions.
  2. `async def create_upgrade_link(...)` for adding items.
  3. Calculate totals if necessary or use Stripe's proration features.
  4. Ensure `metadata={"business_id": ...}` is passed to Stripe to identify the business on webhook.
- **Files**: `src/services/billing_service.py`

### Subtask T009 – Add unit tests for BillingService

- **Purpose**: Ensure service logic is correct without hitting real Stripe API.
- **Steps**:
  1. Create `tests/test_billing_service.py`.
  2. Mock `stripe` library responses using `unittest.mock`.
  3. Verify status retrieval and link generation logic.
- **Files**: `tests/test_billing_service.py`

## Risks & Mitigations

- **Stripe API Down**: Implement try/except blocks and log errors.
- **Invalid Price IDs**: Service should validate configured price IDs against Stripe or fail gracefully.

## Definition of Done Checklist

- [x] `BillingService` implemented with status and link methods
- [x] Stripe API initialized correctly
- [x] Unit tests passing with 80%+ coverage for service methods
- [x] Metadata correctly passed to Stripe sessions

## Review Guidance

- Review the link generation logic to ensure it correctly handles existing subscribers vs new ones.
- Check that environment variables are used for secrets, not hardcoded.

## Activity Log

- 2026-01-20T14:45:30Z – antigravity – lane=planned – Prompt created.
- 2026-01-20T15:49:02Z – Antigravity – shell_pid=3779362 – lane=doing – Started implementation via workflow command
- 2026-01-20T16:38:59Z – Antigravity – shell_pid=3779362 – lane=for_review – Implemented BillingService with full test coverage and configuration-driven item names. Added STRIPE_SECRET_KEY to .env.example.
- 2026-01-20T16:40:39Z – Antigravity – shell_pid=3779362 – lane=doing – Started review via workflow command
