---
work_package_id: "WP01"
title: "Storage Foundation & Models"
lane: "doing"
dependencies: []
subtasks: ["T001", "T002", "T003", "T004", "T017"]
agent: "Antigravity"
shell_pid: "365214"
---
# Work Package 01: Storage Foundation & Models

**Goal**: Establish the database schema for Documents (including refactoring existing Quote/Invoice models) and the service layer for interacting with secure object storage (Backblaze B2 via S3 API).

## Context

This is the foundational work package for Feature 022. We need to store user-uploaded documents securely. We will use a `Document` entity to track metadata and a `StorageService` to handle `boto3` interactions. Just as importantly, we must migrate away from ad-hoc file columns in `Quote` and `Invoice` to use this new unified `Document` registry, allowing a single view of all job collateral.

## Subtasks

### T001: Add `Document` Model & Refactor Quote/Invoice

**Purpose**: Create the `Document` registry and refactor existing models to link to it, removing legacy blob columns.

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
2. Refactor `src/models/quote.py` and `src/models/invoice.py`:
    * **Remove** `blob_url` and `s3_key` (after migration script is ready, or marks as deprecated/nullable for now if preferred, but plan implies removal).
    * **Add** relationship to `Document` (or rely on `Document.job_id` if one-to-many).
        * *Analysis*: Since a quote IS a document effectively, or generates one, we might want `quote.document_id` FK if we want to point to "The PDF for this quote".
        * *Decision*: Add `document_id` FK to `Quote` and `Invoice` to point to their generated PDF file in the registry.
3. Update `src/models/__init__.py`.
4. Run `alembic ensure_migrations` to generate the schema change.
5. Verify migration generation.

**Files**:

* `src/models/document.py` (NEW)
* `src/models/quote.py`
* `src/models/invoice.py`
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

### T017: Create Data Migration (Legacy Quote/Invoice -> Document)

**Purpose**: Migrate existing `Quote.blob_url` and `Invoice.s3_key` data into new `Document` rows before dropping those columns.

**Steps**:

1. Create a data migration script (or include in Alembic migration `upgrade()` logic if safe).
2. Logic:
    * Iterate over all `Quotes` with `blob_url`.
    * Create a `Document` record for each:
        * `doc_type='internal'`
        * `storage_path` = derived from `blob_url` or `s3_key`.
        * `job_id` = `quote.job_id`.
        * `business_id` = `quote.business_id`.
    * Update `Quote.document_id` with result.
    * Repeat for `Invoices`.
3. Verify this works (dry run or test).

**Validation**:

* Tests must pass.
* Migration must be valid and preserve data.

## Activity Log

* 2026-01-22T21:01:21Z – Antigravity – shell_pid=365214 – lane=doing – Started implementation via workflow command
