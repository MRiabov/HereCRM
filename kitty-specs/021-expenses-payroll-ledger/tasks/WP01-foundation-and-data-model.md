---
work_package_id: "WP01"
title: "Foundation & Data Model"
lane: "doing"
dependencies: []
subtasks: ["T001", "T002", "T003", "T004", "T005"]
agent: "Antigravity"
shell_pid: "195966"
---

# Work Package: Foundation & Data Model

## Inspection

- **Goal**: Establish the database schema and SQLAlchemy models required for expenses, payroll ledger, and wage configuration.
- **Role**: Backend Engineer / Database Architect.
- **Outcome**: A migrated database schema and mapped Python models ready for logic implementation.

## Context

This is the foundational work package for Feature 021 "Expenses & Payroll Ledger". We need to add three new tables and update two existing ones to support tracking expenses, employee wages (ledger), and wage configurations.

The data model strategy is "Append Only" for financial records (LedgerEntry) to ensure auditability.

## Detailed Subtasks

### T001: Create Database Migrations

**Goal**: Generate an Alembic migration script to create the new tables and types.
**Files**: `migrations/versions/xxxx_add_expenses_and_ledger.py`
**Schema Details**:

1. **Enum Type**: `WageModel` values: `COMMISSION_PERCENT`, `HOURLY_PER_JOB`, `HOURLY_PER_SHIFT`, `FIXED_DAILY`.
2. **Table**: `wage_configurations`
    - `id` (PK)
    - `employee_id` (FK to users)
    - `model_type` (Enum WageModel)
    - `rate_value` (Float/Numeric)
3. **Table**: `expenses`
    - `id` (PK)
    - `amount` (Float/Numeric)
    - `description` (String)
    - `category` (String)
    - `job_id` (FK to jobs, nullable)
    - `line_item_id` (FK to line_items, nullable)
    - `vendor` (String, nullable)
    - `created_at` (DateTime)
4. **Table**: `ledger_entries`
    - `id` (PK)
    - `employee_id` (FK to users)
    - `amount` (Float/Numeric) - Positive for wage, Negative for payout
    - `entry_type` (String/Enum: WAGE, PAYOUT, ADJUSTMENT)
    - `description` (String)
    - `related_job_id` (FK to jobs, nullable)
    - `created_at` (DateTime)
5. **Updates**:
    - Add `check_in_time` (DateTime, nullable) to `users` table? Or `current_shift_start`. Let's use `current_shift_start` on `users` table for simplicity as per Plan.
    - Add `started_at` (DateTime, nullable) to `jobs` table to track when a job physically started (distinct from 'scheduled_at').

### T002: Create SQLAlchemy Models

**Goal**: Create Python classes for the new tables.
**Files**: `src/models/financial.py` (New file recommended) or split into `src/models/expense.py`, `src/models/ledger.py`.
**Instructions**:

- Create `src/models/financial.py` to house `Expense`, `LedgerEntry`, `WageConfiguration`.
- Use SQLAlchemy 2.0 style (Mapped, mapped_column).
- Ensure relationships are defined (e.g., `Expense.job`, `LedgerEntry.employee`).
- Add `WageModel` enum class here or in `src/models/enums.py` if it exists.

### T003: Update User Model

**Goal**: Add relationships and state fields to User.
**Files**: `src/models/user.py` (or wherever User is defined, likely `src/auth_models.py` or similar - check existing).
**Changes**:

- Add `wage_config: Mapped["WageConfiguration"]` relationship (One-to-One).
- Add `ledger_entries: Mapped[List["LedgerEntry"]]` relationship.
- Add `current_shift_start: Mapped[Optional[datetime]]` handling field.

### T004: Update Job Model

**Goal**: Add relationships and state fields to Job.
**Files**: `src/models/job.py` (check actual location).
**Changes**:

- Add `expenses: Mapped[List["Expense"]]` relationship.
- Add `started_at: Mapped[Optional[datetime]]` handling field.

### T005: Create Seed Data Factory

**Goal**: Verify the models work by writing a simple seed script or test fixture.
**Files**: `tests/unit/test_models_021.py`
**Instructions**:

- Write a test that performs a DB interaction:
    1. Create a User.
    2. Create a WageConfiguration for them.
    3. Create a Job.
    4. Create an Expense linked to that Job.
    5. Create a LedgerEntry for that User.
    6. Assert all IDs are generated and relationships are persistent.

## Validation checks

- [ ] Migration runs `alembic upgrade head` without error.
- [ ] `tests/unit/test_models_021.py` passes.
- [ ] Schema matches the Data Model spec.

## Risks

- **Naming Conflicts**: Check if `Expense` or `Ledger` names conflict with any existing system reserved words or models (unlikely in this codebase).
- **Circular Imports**: Be careful importing User/Job into `financial.py` and vice versa. Use string forward references `"User"` if needed.

## Activity Log

- 2026-01-22T11:40:32Z – Antigravity – shell_pid=195966 – lane=doing – Started implementation via workflow command
- 2026-01-22T11:44:45Z – Antigravity – shell_pid=195966 – lane=for_review – Ready for review: Established foundation schema and models for expenses and payroll ledger. Added migrations (including head merge), updated User/Job models, and added Expense, LedgerEntry, and WageConfiguration models. Verified with unit tests.
- 2026-01-22T11:48:09Z – Antigravity – shell_pid=195966 – lane=doing – Started review via workflow command
