---
work_package_id: "WP01"
title: "Foundation & Data Models"
lane: "for_review"
dependencies: []
subtasks: ["T001", "T002", "T003", "T004"]
agent: "Antigravity"
shell_pid: "318543"
---

# WP01 - Foundation & Data Models

## Objective

Prepare the environment, install dependencies, and update the database schema to support Google Calendar integration.

## Context

We are implementing Spec 024. This first package sets up the ground work: libraries for Google API and database fields to store user credentials.

## Subtasks

### T001: Install Python Dependencies

**Purpose**: add required Google libraries.
**Steps**:

1. Add to `pyproject.toml` (or `requirements.txt` if used, but check project structure first - usually standard `pip install` is fine if no lockfile management is enforced, but `uv` usage suggests modern tooling).
   - `google-api-python-client`
   - `google-auth-oauthlib`
   - `google-auth`
2. Run installation (e.g. `uv pip install ...` or `pip install ...` inside venv).
3. Freeze/update lockfile if applicable.

### T002: Add Environment Variables

**Purpose**: Configure OAuth credentials.
**Steps**:

1. Update `src/config.py` (or `settings.py`) to read:
   - `GOOGLE_CLIENT_ID`
   - `GOOGLE_CLIENT_SECRET`
   - `GOOGLE_REDIRECT_URI`
2. Ensure usage of `pydantic-settings` or `os.getenv` as per project pattern.
3. Allow these to be optional (default None) if not creating a hard crash for devs without creds, BUT log a warning.

### T003: Migration - User Model

**Purpose**: Store OAuth tokens.
**Steps**:

1. Modify `src/models/user.py`:
   - Add `google_calendar_credentials`: `Column(JSON, nullable=True)` (Stores the dict from `credentials.to_json()`)
   - Add `google_calendar_sync_enabled`: `Column(Boolean, default=False)`
2. Create standard Alembic migration (if Alembic is used) OR update schema init script if lighter weight.
   - *Note*: Project uses SQLite+FastAPI. Check `alembic/` folder or `scripts/db_init.py`. If Alembic exists, generate revision.

### T004: Migration - Job Model

**Purpose**: Link CRM jobs to Calendar Events.
**Steps**:

1. Modify `src/models/job.py`:
   - Add `gcal_event_id`: `Column(String, nullable=True)`
2. Include in migration from T003.

## Validation

- [ ] Dependencies installed and importable (`import googleapiclient` works).
- [ ] Config variables load correctly from `.env`.
- [ ] DB Migration runs without error.
- [ ] `User` and `Job` tables show new columns in SQLite browser or inspection tool.

## Risks

- **JSON Column**: Ensure SQLite supports JSON (it usually does via extension or text storage). If using strict SQLAlchemy types, ensure `JSON` is imported from a dialect-agnostic source or handle as Text if needed.

## Activity Log

- 2026-01-24T09:56:55Z – Antigravity – shell_pid=318543 – lane=doing – Started implementation via workflow command
- 2026-01-24T10:05:28Z – Antigravity – shell_pid=318543 – lane=for_review – Ready for review: Implemented WP01 foundation. Added Google API dependencies, configured OAuth credentials in settings, and updated User/Job models with new columns. Database migrations generated and applied.
