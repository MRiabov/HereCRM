---
work_package_id: "WP02"
title: "Document Service Core"
lane: "done"
dependencies: ["WP01"]
subtasks: ["T005", "T006", "T007"]
shell_pid: "15223"
reviewed_by: "MRiabov"
review_status: "approved"
---
# Work Package 02: Document Service Core

**Goal**: Implement the business logic for creating documents, associating them with jobs, and managing their lifecycle.

## Context

With the data model and storage layer in place (WP01), we need the glue logic. The `DocumentService` will handle the "smart" parts: automatically deciding which Job a new document belongs to.

## Subtasks

### T005: Implement `DocumentService` Base

**Purpose**: Create the service that orchestrates DB and Storage.

**Steps**:

1. Create `src/services/document_service.py`.
2. Inject `StorageService` and `db_session`.
3. Implement `create_document`:
    * Args: `business_id`, `customer_id`, `file_obj`, `filename`, `mime_type`, `doc_type='internal'`, `external_url=None`.
    * If `internal`: Call `StorageService.upload_file` → get key.
    * If `external`: Use `external_url` as path.
    * Attempt Auto-Association (see T006).
    * Create `Document` DB record.
    * Commit.
    * Return `Document` instance.
4. Implement `get_documents_for_job(job_id) -> List[Document]`.
5. Implement `get_documents_for_customer(customer_id) -> List[Document]`.

**Files**:
* `src/services/document_service.py` (NEW)

### T006: Implement Auto-Association Logic

**Purpose**: Automatically link uploaded docs to the most relevant active job.

**Steps**:

1. In `DocumentService` (or `JobService` if preferred, but keep logic close), add `find_active_job_for_customer(customer_id) -> Job | None`.
    * Logic: Find jobs for this customer where status NOT IN (`COMPLETED`, `CANCELLED`).
    * Sort by `updated_at` (desc).
    * Return the most recent one.
2. Integrate this into `create_document`.
    * If `job_id` is NOT provided in args: CALL `find_active_job_for_customer`.
    * If found, set `document.job_id`.
    * If not found, leave null (attached to customer only).

### T007: Integration Tests for Document Service

**Purpose**: Verify association logic and DB persistence.

**Steps**:

1. Create `tests/services/test_document_service.py`.
2. Test `create_document` (Internal):
    * Mock `StorageService`.
    * Call create.
    * Verify DB record created with correct storage path.
3. Test Auto-Association:
    * Create a Customer and an Active Job.
    * Create a Document (without `job_id`).
    * Verify `document.job_id` matches the Active Job.
    * Create a Completed Job.
    * Create Document.
    * Verify it does NOT attach to Completed Job (if no active one).

**Validation**:
* Auto-association logic correctly picks active job.
* Documents are persisted.

## Activity Log

- 2026-01-23T10:21:19Z – unknown – shell_pid=15223 – lane=done – WP02 - Document Service Core completed. Tests passed.
