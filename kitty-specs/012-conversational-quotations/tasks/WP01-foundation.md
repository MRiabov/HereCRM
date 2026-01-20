---
work_package_id: "WP01"
title: "Foundation & Core Service"
lane: "doing"
dependencies: []
subtasks: ["T001", "T002", "T003", "T004", "T005"]
agent: "Antigravity"
shell_pid: "3779362"
---

### Objective

Establish the database schema and core service layer for the Conversational Quotations feature. This foundation enables creating and persisting `Quote` entities with their associated `RefItem`s (Line Items).

### Context

We are introducing a new entity `Quote` which is similar to an Invoice but represents a proposal. It needs to link to `Customer`, `Business`, and optionally a `Job` (upon acceptance).

### Subtasks

#### T001: Create Quote Models

**Purpose**: Define the database structure for Quotes.
**Steps**:

1. Edit `src/models.py`.
2. Define `QuoteStatus` enum: `DRAFT`, `SENT`, `ACCEPTED`, `REJECTED`, `EXPIRED`.
3. Define `Quote` class (SQLModel):
   - Fields: `id`, `customer_id`, `business_id`, `status` (default DRAFT), `total_amount`, `external_token` (secrets.token_urlsafe), `blob_url`, `job_id`, `created_at`, `updated_at`.
   - Relationships: `customer`, `business`, `items`, `job`.
4. Define `QuoteLineItem` class:
   - Fields: `id`, `quote_id`, `service_id` (optional), `description`, `quantity`, `unit_price`, `total`.
   - Relationships: `quote`.

#### T002: Update Relationships

**Purpose**: Update existing models to reference Quotes.
**Steps**:

1. Edit `Business` in `src/models.py`: add `quotes: List["Quote"]`.
2. Edit `Customer` in `src/models.py`: add `quotes: List["Quote"]`.

#### T003: Database Migration

**Purpose**: Apply schema changes.
**Steps**:

1. Run `alembic revision --autogenerate -m "Add quote tables"`.
2. Verify the migration file.
3. Run `alembic upgrade head`.

#### T004: Implement QuoteService

**Purpose**: Centralize business logic for Quotes.
**Steps**:

1. Create `src/services/quote_service.py`.
2. Implement class `QuoteService`.
3. Add method `create_quote(customer_id, business_id, lines: List[Dict]) -> Quote`:
   - Calculate line totals and grand total.
   - Generate `external_token`.
   - Create `Quote` and `QuoteLineItem` records.
   - Commit to DB.
4. Add method `get_quote(quote_id) -> Quote`.
5. Add method `get_recent_quote(customer_id) -> Quote` (returns latest SENT quote).

#### T005: Unit Tests

**Purpose**: Verify foundation works.
**Steps**:

1. Create `tests/unit/test_quote_service.py`.
2. Test `create_quote`: check calculations, token generation, DB persistence.
3. Test `get_quote`: retrieval.

### Verification

- Run `pytest tests/unit/test_quote_service.py`.
- Ensure migration runs without errors.

## Activity Log

- 2026-01-20T18:18:08Z – Antigravity – shell_pid=3779362 – lane=doing – Started implementation via workflow command
- 2026-01-20T18:29:02Z – Antigravity – shell_pid=3779362 – lane=for_review – Ready for review: Established Quote and QuoteLineItem models, fixed migration history, and implemented QuoteService with unit tests.
- 2026-01-20T18:31:36Z – Antigravity – shell_pid=3779362 – lane=doing – Started review via workflow command
