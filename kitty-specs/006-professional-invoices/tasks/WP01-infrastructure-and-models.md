---
type: work-package
id: WP01
lane: "done"
subtasks:
  - T001
  - T002
  - T003
  - T004
  - T005
  - T006
agent: "antigravity"
review_status: "approved without changes"
reviewed_by: "antigravity"
---

# Work Package 01: Infrastructure & Data Model

## Goal

Establish the foundational infrastructure for invoice generation and storage, including S3 integration and database schema updates.

## Context

We are adding professional invoicing capabilities. This requires storing generated PDF files in S3 (Backblaze B2 compatible) and tracking them in the database.

## Subtasks

### T001: Install Python dependencies

- Add `boto3`, `weasyprint`, `jinja2` to `pyproject.toml`.
- Run `uv sync` or `pip install` to update environment.
- **Note**: `weasyprint` requires system libraries (`libpango-1.0-0`, `libcairo2`, etc.). If running in a container, update Dockerfile. If local, note requirements.

### T002: Update Configuration

- Update `.env.example` with:
  - `S3_ENDPOINT_URL`
  - `S3_ACCESS_KEY_ID`
  - `S3_SECRET_ACCESS_KEY`
  - `S3_BUCKET_NAME`
  - `S3_REGION_NAME`
- Add these fields to `Settings` class in `src/config.py` (using `pydantic-settings` or `os.getenv`).

### T003: Implement `S3Service`

- Create `src/services/storage.py`.
- Class `S3Service`:
  - Initialize `boto3` client/resource using config.
  - `upload_file(file_content: bytes, key: str, content_type: str = 'application/pdf') -> str`: Uploads file, returns public URL.
  - `get_public_url(key: str) -> str`: Helper to construct URL if needed.
- Implement proper error handling (log errors, re-raise as application specific exceptions).

### T004: Create `Invoice` model

- In `src/database/models.py`.
- Define `Invoice` class inheriting from `SQLModel` (and `table=True`).
- Fields:
  - `id`: Optional[int], Primary Key.
  - `job_id`: int, Foreign Key to `job.id`.
  - `created_at`: datetime (default now).
  - `s3_key`: str.
  - `public_url`: str.
  - `status`: str (default "SENT").

### T005: Update `Job` model

- In `src/database/models.py`, update `Job` class.
- Add relationship: `invoices: List["Invoice"] = Relationship(back_populates="job")`.
- Update `Invoice` to have `job: "Job" = Relationship(back_populates="invoices")`.

### T006: Database Migration

- Run `alembic revision --autogenerate -m "Add Invoice model"`.
- Inspect the generated migration file in `alembic/versions/`.
- Run `alembic upgrade head`.

## Verification

- Verify `Invoice` table exists in database.
- Create a test script `tests/test_s3_connection.py` to verify `S3Service` can be instantiated (mocked if no creds).

## Activity Log

- 2026-01-17T10:04:24Z – codex – lane=doing – Started implementation
- 2026-01-17T10:07:31Z – codex – lane=for_review – Infrastructure and data model complete
- 2026-01-17T10:25:00Z – antigravity – lane=done – Approved without changes. Verification tests passed.
- 2026-01-17T10:18:55Z – antigravity – lane=done – Review complete and verified
