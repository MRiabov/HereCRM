---
work_package_id: "WP00"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
title: "Foundation & Data Model"
phase: "Phase 1 - Infrastructure"
lane: "done"
dependencies: []
agent: "Antigravity"
shell_pid: "3779362"
reviewed_by: "MRiabov"
review_status: "approved"
history:
  - timestamp: "2026-01-20T14:45:30Z"
    lane: "planned"
    agent: "antigravity"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP00 – Foundation & Data Model

## Objectives & Success Criteria

- Install dependencies and configure the project for Stripe integration.
- Establish the data model for business subscriptions and conversational states.
- Prepare the database for entitlement tracking.

## Context & Constraints

- Follows the [spec.md](../spec.md) and [plan.md](../plan.md).
- Data model details are in [data-model.md](../data-model.md).
- Ensure migrations are compatible with existing PostgreSQL/Alembic setup.

## Subtasks & Detailed Guidance

### Subtask T001 – Install stripe package

- **Purpose**: Add Stripe dependency to the project.
- **Steps**:
  1. Add `stripe` to `pyproject.toml`.
  2. Run `pip install stripe` or `uv pip install stripe` (per `.venv` rules).
  3. Verify installation with `python -c "import stripe; print(stripe.VERSION)"`.
- **Files**: `pyproject.toml`

### Subtask T002 – Create billing_config.yaml

- **Purpose**: Centralize the product catalog.
- **Steps**:
  1. Create `src/config/billing_config.yaml`.
  2. Add `seats` and `addons` sections as defined in `data-model.md`.
  3. Include descriptive names, Stripe price IDs, and associated scopes.
- **Files**: `src/config/billing_config.yaml`

### Subtask T003 – Update ConversationStatus enum

- **Purpose**: Add the `BILLING` state to the conversational flow.
- **Steps**:
  1. Add `BILLING = "billing"` to `ConversationStatus` enum in `src/models.py`.
- **Files**: `src/models.py`

### Subtask T004 – Generate Alembic migration

- **Purpose**: Update `businesses` table schema.
- **Steps**:
  1. Run `alembic revision --autogenerate -m "add_billing_fields_to_business"`.
  2. Ensure the migration adds: `stripe_customer_id` (String), `stripe_subscription_id` (String), `subscription_status` (String, default='free'), `seat_limit` (Integer, default=1), `active_addons` (JSON, default=[]).
- **Files**: `migrations/versions/*.py`

### Subtask T005 – Update Business model and repository

- **Purpose**: Map new database fields to the application logic.
- **Steps**:
  1. Update `Business` class in `src/models.py` with Mapped columns.
  2. Update `BusinessRepository` in `src/repositories.py` if custom mapping/queries are needed for these fields.
- **Files**: `src/models.py`, `src/repositories.py`

## Risks & Mitigations

- **Migration Conflict**: Ensure the migration is generated against the latest schema.
- **Data Defaults**: Ensure existing businesses are defaulted to 'free' status and 1 seat limit.

## Definition of Done Checklist

- [ ] `stripe` package installed and in dependencies
- [ ] `billing_config.yaml` exists with products
- [ ] `ConversationStatus` includes `BILLING`
- [ ] Database schema updated via Alembic
- [ ] `Business` model reflects new fields

## Review Guidance

- Verify the `active_addons` field is correctly handled as JSON and defaults to an empty list.
- Check that the `BILLING` enum member is correctly named and typed.

## Activity Log

- 2026-01-20T14:45:30Z – antigravity – lane=planned – Prompt created.
- 2026-01-20T15:25:45Z – Antigravity – shell_pid=3779362 – lane=doing – Started implementation via workflow command
- 2026-01-20T15:47:59Z – Antigravity – shell_pid=3779362 – lane=for_review – Ready for review: Foundation & Data Model implemented with billing fields, config, and migration.
- 2026-01-20T16:27:37Z – Antigravity – shell_pid=3779362 – lane=done – Marked as done per user request.
