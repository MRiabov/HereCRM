---
work_package_id: WP03
title: Sync Logic - Base & Dependencies
lane: "done"
dependencies: []
subtasks:
- T011
- T012
- T013
- T014
agent: "gemini-cli"
shell_pid: "136968"
review_status: "has_feedback"
reviewed_by: "MRiabov"
---

## Objective

Implement the base synchronization architecture and the specific sync logic for "dependency" entities (Customers and Services), which must be synced before Invoices/Payments.

## Context

Synchronization is one-way (HereCRM -> QuickBooks). It follows a specific order: Customers/Services first, then Invoices, then Payments. We need a flexible pattern to handle mapping, API calls, error handling, and status updates for each entity type.

## Detailed Guidance

### Subtask T011: Define QuickBooksSyncer base class and mapper interfaces

**Purpose**: Create a reusable base class or interface for syncers.
**Files**: `src/services/accounting/syncer_base.py`, `src/services/accounting/sync_mappers.py`
**Instructions**:

1. Create `AbstractSyncer` class.
    - `sync(self, business_id, record_id)`: Main method.
    - `_map_record(self, record) -> dict`: Abstract method.
    - `_push_to_qb(self, qb_client, data) -> str`: Abstract method (returns QB ID).
    - `_update_status(self, record, status, qb_id=None, error=None)`: Helper to update DB.
2. Define common error handling (try/except QBClientError) in the `sync` method.
3. Error logic:
    - If success: Update status='synced', `quickbooks_id`, `synced_at`.
    - If error: Update status='failed', `sync_error`.

### Subtask T012: Implement CustomerSyncer and data mapper

**Purpose**: Sync `Customer` entities to QuickBooks `Customer`.
**Files**: `src/services/accounting/customer_syncer.py`
**Instructions**:

1. Implement `CustomerSyncer(AbstractSyncer)`.
2. Mapping (`_map_record`):
    - `DisplayName`: `customer.name`.
    - `PrimaryPhone`: `customer.phone`.
    - `PrimaryEmailAddr`: `customer.email`.
    - Map Address if available.
3. Push logic (`_push_to_qb`):
    - Search if customer exists by name (to avoid duplicates if `quickbooks_id` is null but name matches).
    - If exists update.
    - If not exists create.
    - Use `python-quickbooks` `Customer` object.
4. Validation: Fail if Name is empty.

### Subtask T013: Implement ServiceSyncer and data mapper

**Purpose**: Sync `Service` entities to QuickBooks `Item` (Service type).
**Files**: `src/services/accounting/service_syncer.py`
**Instructions**:

1. Implement `ServiceSyncer(AbstractSyncer)`.
2. Mapping:
    - `Name`: `service.name`.
    - `Type`: 'Service'.
    - `UnitPrice`: `service.default_price`.
    - `Description`: `service.description`.
3. Push logic:
    - Query by name.
    - Create or Update `Item`.

### Subtask T014: Add unit tests for Customer and Service mapping/sync logic

**Purpose**: Verify mapping correctness and simple sync flow.
**Files**: `tests/unit/test_sync_base.py`
**Instructions**:

1. Test `CustomerSyncer` mapping: Ensure fields line up.
2. Test `ServiceSyncer` mapping.
3. Test error handling: Ensure `_update_status` is called with 'failed' on exception.

## Definition of Done

- Base class implementation handles the boilerplate (status updates, error catching).
- Customers and Services can be successfully mapped and mocked-pushed.
- Duplicate checks (by name) are implemented.
- Tests pass.

## Verification

- Run `pytest tests/unit/test_sync_base.py`.

## Activity Log

- 2026-01-22T07:50:59Z – Cascade – shell_pid=31544 – lane=doing – Started implementation via workflow command
- 2026-01-22T08:02:36Z – Cascade – shell_pid=31544 – lane=for_review – Ready for review: Implemented base sync architecture with AbstractSyncer class, CustomerSyncer, ServiceSyncer, comprehensive unit tests, and sync status fields in models
- 2026-01-22T09:49:33Z – gemini – shell_pid=96079 – lane=doing – Started review via workflow command
- 2026-01-22T09:51:49Z – gemini – shell_pid=96079 – lane=planned – Changes requested: Sync/Async mismatch and missing repo methods
- 2026-01-22T09:53:18Z – gemini – shell_pid=101152 – lane=doing – Started implementation via workflow command
- 2026-01-22T09:55:40Z – gemini – shell_pid=101152 – lane=for_review – Ready for review: Refactored syncers to be asynchronous, fixed repository method calls, and added QuickBooks query escaping.
- 2026-01-22T09:58:25Z – gemini-cli – shell_pid=106031 – lane=doing – Started review via workflow command
- 2026-01-22T10:01:47Z – gemini-cli – shell_pid=106031 – lane=planned – Moved to planned
- 2026-01-22T10:03:45Z – gemini-cli – shell_pid=112998 – lane=doing – Started implementation via workflow command
- 2026-01-22T10:07:02Z – gemini-cli – shell_pid=112998 – lane=for_review – Ready for review: Implemented base sync architecture with non-blocking I/O, added Customer/Service syncers with email mapping, and created Alembic migration.
- 2026-01-22T10:08:32Z – gemini – shell_pid=118693 – lane=doing – Started review via workflow command
- 2026-01-22T10:12:53Z – gemini – shell_pid=118693 – lane=planned – Moved to planned
- 2026-01-22T10:19:26Z – gemini – shell_pid=118693 – lane=doing – Implementing fixes from review
- 2026-01-22T10:20:59Z – gemini – shell_pid=118693 – lane=for_review – Implemented review fixes: added model fields, dependency, init file, and optimized syncer.
- 2026-01-22T10:23:38Z – gemini-cli – shell_pid=136968 – lane=doing – Started review via workflow command
- 2026-01-22T10:26:45Z – gemini-cli – shell_pid=136968 – lane=done – Review passed: File organization fixed, broad exception handling replaced with specific ones, and integration tests verified after fixing RBAC regression.
