---
work_package_id: WP01
subtasks:
  - T001
  - T002
  - T003
  - T004
  - T005
lane: for_review
history:
  - date: 2026-01-13
    status: planned
    agent: spec-kitty
  - date: 2026-01-13
    status: doing
    agent: antigravity
  - date: 2026-01-13
    status: for_review
    agent: antigravity
  - date: 2026-01-13
    status: planned
    agent: antigravity
    note: "Needs changes: Missing dependencies and quality issues."
  - date: 2026-01-13
    status: doing
    agent: antigravity
    note: "Addressing review feedback"
  - date: 2026-01-13
    status: for_review
    agent: antigravity
    note: "Fixed missing dependencies, utcnow() deprecation, and type inconsistencies."
---
## Review Feedback

**Status**: ❌ **Needs Changes**

**Key Issues**:

1. **Missing Dependencies**: `sqlalchemy` and `aiosqlite` are missing from `pyproject.toml`. The app will not run without them.
2. **Missing Package Marker**: `src/__init__.py` is missing, causing import issues for tests and potentially for the runner.
3. **Deprecated Methods**: Used `datetime.utcnow()` which is deprecated in Python 3.12. Use `datetime.now(timezone.utc)` instead.
4. **Type Inconsistencies**:
   - `Job.value` is `Integer` in DB but comment says "python float". Should use `Float` or `Numeric`.
   - `ConversationState.draft_data` should be `JSON` type for better integration.

**What Was Done Well**:

- Good use of `asynccontextmanager` for FastAPI lifespan.
- Clean repository pattern with tenant isolation filtering.
- Models correctly implement foreign keys to `business_id`.

**Action Items**:

- [ ] Add `sqlalchemy` and `aiosqlite` to `pyproject.toml`.
- [ ] Create `src/__init__.py`.
- [ ] Update `datetime.utcnow()` to `datetime.now(timezone.utc)`.
- [ ] Fix `Job.value` type to match its intended use (Float/Numeric).
- [ ] Change `ConversationState.draft_data` to `JSON` type.
- [ ] Ensure all tests pass without manual `PYTHONPATH` manipulation (fix `src` as package).

# Work Package: Scaffolding & Core Models

## Objective

Establish the foundational infrastructure for the WhatsApp CRM, including the FastAPI application structure, asynchronous SQLite database connection, and the complete SQLAlchemy data model with multi-tenancy support.

## Context

This is the first step in the implementation. We are building a multi-tenant system where `Business` is the root entity. All data access must be scoped to a specific business. We are using `SQLAlchemy` (Async) and `FastAPI`.

## Subtasks

### T001: Setup FastAPI & Async DB

- Initialize a new FastAPI project structure in `src/`.
- Configure `sqlalchemy` with `aiosqlite` driver.
- Create a `database.py` file with `get_db` dependency.
- Ensure `pyproject.toml` has necessary dependencies (`fastapi`, `uvicorn`, `sqlalchemy`, `aiosqlite`, `pydantic-settings`).

### T002: Implement Business & User Models

- Create `src/models.py`.
- Define `Business` model: `id` (PK), `name`, `created_at`.
- Define `User` model: `phone_number` (PK), `business_id` (FK), `role`, `created_at`, `preferences` (JSON, default=`{"confirm_by_default": false}`).
- **Constraint**: `User.phone_number` must be unique across the system (global identifier).

### T003: Implement Domain Models

- Add to `src/models.py`:
  - `Customer`: `id`, `business_id`, `name`, `phone`, `details`.
  - `Job`: `id`, `business_id`, `customer_id`, `description`, `status`, `value`, `location`.
  - `Request`: `id`, `business_id`, `content`, `status`.
- **Constraint**: All these models MUST have a `business_id` Foreign Key.

### T004: Implement ConversationState Model

- Add `ConversationState` to `src/models.py`:
  - `phone_number` (PK) - Links to User.
  - `state` (Enum: IDLE, WAITING_CONFIRM).
  - `draft_data` (JSON/Text) - Stores pending command data.
  - `last_updated` (DateTime).

### T005: Tenant Isolation Repositories

- Create `src/repositories.py`.
- Implement a `BaseRepository` or specific repositories (`UserRepository`, `JobRepository`, etc.).
- **Critical**: Every query (SELECT, UPDATE, DELETE) must accept `business_id` and filter by it.
- **Exception**: `UserRepository.get_by_phone` is global (to find the user/business).

## Definition of Done

- [ ] FastAPI app runs (`uvicorn src.main:app`).
- [ ] Database file is created on startup.
- [ ] All models are migratable/syncable (using `Base.metadata.create_all` for MVP).
- [ ] Tests in `tests/test_models.py` pass, specifically verifying that a User from Business A cannot access Customer from Business B.
