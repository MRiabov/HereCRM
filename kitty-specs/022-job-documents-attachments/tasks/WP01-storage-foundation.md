---
work_package_id: "WP01"
title: "Storage Foundation & Models"
lane: "doing"
dependencies: []
subtasks: ["T001", "T002", "T003", "T004"]
agent: "Antigravity"
shell_pid: "365214"
---
# Work Package 01: Storage Foundation & Models

**Goal**: Establish the database schema for Documents and the service layer for interacting with secure object storage (Backblaze B2 via S3 API).

## Context

This is the foundational work package for Feature 022. We need to store user-uploaded documents securely. We will use a `Document` entity to track metadata and a `StorageService` to handle `boto3` interactions. All file content will be private; retrieval is only via presigned URLs.

## Subtasks

### T001: Add `Document` Model and Migration

**Purpose**: Create the database table to track documents.

**Steps**:

1. Create `src/models/document.py`:
    * Class `Document(Base)`.
    * Columns:
        * `id`: Integer, PK
        * `business_id`: Integer, FK to businesses.id
        * `customer_id`: Integer, FK to users.id
        * `job_id`: Integer, FK to jobs.id, Nullable
        * `doc_type`: String (Enum: `'internal'`, `'external_link'`)
        * `storage_path`: String (S3 Key or URL)
        * `filename`: String
        * `mime_type`: String
        * `size_bytes`: Integer
        * `created_at`: DateTime (default UTC now)
    * Relationships:
        * `business`: relationship to Business
        * `customer`: relationship to User
        * `job`: relationship to Job
2. Update `src/models/__init__.py` to export `Document`.
3. Run `alembic ensure_migrations` (or equivalent workflow) to generate a new migration version.
4. Verify migration generation (it should detect the new table).

**Files**:
* `src/models/document.py` (NEW)
* `src/models/__init__.py`
* `alembic/versions/...` (NEW)

### T002: Add `boto3` Dependency

**Purpose**: Add `boto3` and `boto3-stubs` to project dependencies.

**Steps**:

1. Check `pyproject.toml` or `requirements.txt`.
2. Add `boto3>=1.34.0` and `types-boto3[s3]`.
3. Update lock file/install (e.g., `uv sync` or `pip install`).
4. Add configuration variables to `src/config/settings.py` (or equivalent):
    * `STORAGE_BUCKET_NAME`
    * `STORAGE_ENDPOINT_URL` (for B2 compatibility)
    * `STORAGE_KEY_ID`
    * `STORAGE_APP_KEY`
    * `STORAGE_REGION` (optional, default to us-east-1 or standard)

### T003: Implement `StorageService`

**Purpose**: Create a wrapper service for S3 operations to decouple app logic from `top-level` boto3 calls.

**Steps**:

1. Create `src/services/storage_service.py`.
2. Define `StorageService` class.
3. Initialize `boto3.client('s3', ...)` in `__init__` using config values.
4. Implement methods:
    * `upload_file(file_obj: IO, filename: str, mime_type: str) -> str`:
        * Generate a unique path: `businesses/{bid}/docs/{uuid}-{filename}`.
        * Upload file using `put_object` or `upload_fileobj`.
        * Return the storage key/path.
    * `get_presigned_url(storage_path: str, expiration: int = 3600) -> str`:
        * Generate presigned GET URL for the key.
    * `delete_file(storage_path: str)`:
        * Delete object (cleanup).

**Files**:
* `src/services/storage_service.py` (NEW)

### T004: Test Storage Service

**Purpose**: Verify StorageService works using `moto` (mock AWS).

**Steps**:

1. Create `tests/services/test_storage_service.py`.
2. Use `moto` decorator (`@mock_s3`) or fixture.
3. Test `upload_file`:
    * Call upload.
    * Verify object exists in mocked bucket.
4. Test `get_presigned_url`:
    * Verify it returns a URL string containing the key.

**Validation**:
* Tests must pass.
* Migration must be valid.

## Activity Log

- 2026-01-22T21:01:21Z – Antigravity – shell_pid=365214 – lane=doing – Started implementation via workflow command
