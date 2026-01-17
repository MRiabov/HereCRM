---
work_package_id: WP01
subtasks:
  - T001
  - T002
  - T003
  - T004
  - T005
lane: planned
history:
  - date: 2026-01-17
    action: created
    agent: Antigravity
---

# Work Package 01: Infrastructure & Data Models

## Objective

Establish the database schema, install dependencies, and create the service skeleton for data management.

## Context

This is the foundational work package for Feature 007 - Customer Import/Export. We need to set up the data models to track import jobs and export requests, and ensure we have the necessary libraries (`pandas`, `openpyxl`) installed.

## Subtasks

### T001: Install Dependencies

- **Action**: Add `pandas`, `openpyxl`, and `python-multipart` to `requirements.txt` if not present.
- **Verification**: Run `pip install -r requirements.txt` and ensure it succeeds.

### T002: Define ImportJob Model

- **File**: `src/models.py`
- **Action**: Create a new SQLAlchemy model `ImportJob`.
- **Fields**:
  - `id`: Integer, Primary Key
  - `user_id`: Integer, ForeignKey('users.id') (nullable if system-wide) - *Actually, spec implies user context, so link to User or Customer? Plan says "reuse AuthService and UserRepository", so we likely have a user.* Let's assume `user_id` maps to the admin/user initiating the request.
  - `file_url`: String (S3 key or local path)
  - `status`: String/Enum (PENDING, PROCESSING, COMPLETED, FAILED)
  - `result_summary`: JSON/String (e.g. "Imported 50, Failed 2")
  - `created_at`: DateTime
- **Context**: Used to track async import status.

### T003: Define ExportRequest Model

- **File**: `src/models.py`
- **Action**: Create a new SQLAlchemy model `ExportRequest`.
- **Fields**:
  - `id`: Integer, Primary Key
  - `user_id`: Integer, ForeignKey('users.id')
  - `query_text`: String (The NL query)
  - `status`: String/Enum
  - `file_format`: String (csv, xlsx, json)
  - `file_url`: String (Resulting downloadable URL)
  - `created_at`: DateTime

### T004: DB Migrations

- **Action**: Run `alembic revision --autogenerate -m "Add import_export models"` and apply it.
- **Verification**: Verify tables exist in the DB (using sqlite3 or psql tool).

### T005: Service Skeleton

- **File**: `src/services/data_management.py`
- **Action**: Create class `DataManagementService` with empty methods:
  - `async def parse_file(self, file_path: str) -> pd.DataFrame`
  - `async def import_data(self, df: pd.DataFrame, dry_run: bool = False) -> dict`
  - `async def process_export(self, request_id: int)`

## Definition of Done

- Models `ImportJob` and `ExportRequest` exist in `src/models.py`.
- Migration file created and applied.
- Dependencies installed.
- `DataManagementService` file exists and class is importable.

## Risks

- Existing model conflicts: Ensure no naming collisions.
- Dependency conflicts: Check for version compatibility with existing libs.
