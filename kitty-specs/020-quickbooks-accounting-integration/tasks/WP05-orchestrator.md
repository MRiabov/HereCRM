---
work_package_id: WP05
title: Orchestration & Scheduler
lane: "doing"
dependencies: []
subtasks:
- T019
- T020
- T021
- T022
- T023
agent: "Gemini"
shell_pid: "140601"
review_status: "has_feedback"
reviewed_by: "MRiabov"
---

## Objective

Implement the `QuickBooksSyncManager` which runs the sync job. It must select records, process them in order (Customer -> Svc -> Inv -> Pmt), handle errors, manage `SyncLog` entries, and run via schedule.

## Context

This is the "engine" that runs every hour. It connects WP01-WP04 together. It needs to be robust—if one record fails, the batch should continue (unless it's a hard auth failure).

## Detailed Guidance

### Subtask T019: Implement QuickBooksSyncManager to orchestrate entity sync order

**Purpose**: The main controller class.
**Files**: `src/services/accounting/quickbooks_sync.py`
**Instructions**:

1. Create `QuickBooksSyncManager`.
2. `run_sync(business_id, sync_type)`:
    - Create `SyncLog` (status='processing').
    - Authenticate (refresh tokens). If fail -> Log error, notify, exit.
    - Fetch pending records (Status != 'synced').
    - Order: Customers, Services, Invoices, Payments.
    - Iterate and call respective Syncers.

### Subtask T020: Implement batch processing, error handling, and SyncLog recording

**Purpose**: Ensure we track what happened.
**Files**: `src/services/accounting/quickbooks_sync.py`
**Instructions**:

1. Inside `run_sync`:
    - Count success/failures.
    - Collect error messages (limit to top 5 distinctive errors to avoid logging spam).
    - Update `SyncLog` at end (status='success' or 'partial_success' or 'failed', duration).
    - Update `Business.quickbooks_last_sync`.

### Subtask T021: Configure APScheduler job for hourly sync execution

**Purpose**: Run it automatically.
**Files**: `src/scheduler.py`
**Instructions**:

1. Add job `run_hourly_quickbooks_sync`.
2. Logic:
    - Query all businesses with `quickbooks_connected=True`.
    - Loop through them and call `QuickBooksSyncManager.run_sync(bid, 'scheduled')`.
    - Handle exceptions so one business failing doesn't stop others.

### Subtask T022: Implement manual sync trigger logic

**Purpose**: Allow user to force a run.
**Files**: `src/services/accounting/quickbooks_sync.py`, `src/services/accounting/service.py` (facade)
**Instructions**:

1. Expose an async method `trigger_manual_sync(business_id)`.
2. Should run in background (fire and forget from user perspective, or return "Started").
3. Reuse `QuickBooksSyncManager`.

### Subtask T023: Add integration tests for full sync cycle

**Purpose**: Verify the orchestrator calls everything correctly.
**Files**: `tests/integration/test_sync_orchestration.py`
**Instructions**:

1. Mock the Syncers (we tested them in WP03/04).
2. Mock DB with some pending records.
3. Run `manager.run_sync`.
4. Assert `SyncLog` created and updated.
5. Assert Syncers called in correct order.

## Definition of Done

- Sync job exists and runs logically.
- Sync logs are reliable.
- Scheduler is configured.
- Tests pass.

## Verification

- Run `pytest tests/integration/test_sync_orchestration.py`.

## Activity Log

- 2026-01-22T07:36:57Z – Cascade – shell_pid=26412 – lane=doing – Started implementation via workflow command
- 2026-01-22T09:55:59Z – Cascade – shell_pid=26412 – lane=for_review – Ready for review: Implemented QuickBooksSyncManager for orchestrating entity sync (Customers, Services), configured hourly APScheduler job, and implemented manual sync trigger. Added integration tests.
- 2026-01-22T10:01:08Z – gemini-agent – shell_pid=109108 – lane=doing – Started review via workflow command
- 2026-01-22T10:03:14Z – gemini-agent – shell_pid=109108 – lane=planned – Moved to planned
- 2026-01-22T10:16:27Z – Gemini – shell_pid=127390 – lane=doing – Started implementation via workflow command
- 2026-01-22T10:24:35Z – Gemini – shell_pid=127390 – lane=for_review – Ready for review: Implemented QuickBooksSyncManager for orchestration, configured hourly APScheduler job, and implemented manual sync trigger. Refactored to use QuickBooksAuthService and QuickBooksCredential for security. Added integration tests.
- 2026-01-22T10:25:30Z – Gemini – shell_pid=140601 – lane=doing – Started review via workflow command
- 2026-01-22T10:30:59Z – Gemini – shell_pid=140601 – lane=planned – Changes requested: critical bug and missing dependencies
- 2026-01-22T10:34:32Z – Gemini – shell_pid=140601 – lane=doing – Moved to doing
