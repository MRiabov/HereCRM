---
work_package_id: "WP04"
title: "Autoroute Command - Execution"
lane: "done"
dependencies: ["WP03"]
subtasks:
  - "T014"
  - "T015"
  - "T016"
agent: "Antigravity"
shell_pid: "4073129"
reviewed_by: "MRiabov"
review_status: "approved"
---

# Work Package 04: Autoroute Command - Execution

## Objective

Enable the application of the calculated schedule to the database, effectively assigning jobs to employees.

## Context

After previewing the schedule, the user needs to commit it. This WP adds the write-capability to the `autoroute` tool.

## Subtasks

### T014: Update `AutorouteTool` for execution

**Purpose**: Allow the tool to run in "apply" mode.
**Files**: `src/tools/routing_tools.py`
**Steps**:

1. Update `AutorouteInput` schema:
    - Add `apply`: bool (default False).
    - Add `notify`: bool (default True).
2. Update `run` method:
    - If `apply` is True, invoke `apply_schedule`.
    - If `apply` is False, return Preview (WP03 logic).

### T015: Implement `apply_schedule` transaction logic

**Purpose**: Persist the routing solution to the database atomically.
**Files**: `src/tools/routing_tools.py`, `src/services/job_service.py` (or similar)
**Steps**:

1. Re-calculate the routes (to ensure freshness).
2. Wrap in a generic DB transaction (unit of work).
3. For each route in solution:
    - Update each `Job`:
        - Set `employee_id`.
        - Set `scheduled_at` (calculated start time).
        - Set `status` to 'scheduled' (if applicable).
4. Return a success summary ("X jobs assigned.").

### T016: Add notification hooks

**Purpose**: Notify customers/employees (placeholder/basic impl).
**Files**: `src/tools/routing_tools.py`
**Steps**:

1. If `notify` is True:
    - Loop through assigned jobs/employees.
    - Call `MessageService` (or print log if not ready) to queue notifications.
    - *Constraint*: Just log "Notification sent to X" for now unless MessageService is fully integrated and Spec 013 explicitly demands real messages (Spec says "handoff to Msg Spec", so simple hook/log is enough).

## Test Strategy

- **Integration Tests**:
  - Test `AutorouteTool(apply=True)`.
  - Verify DB state changes (jobs are assigned).
  - Verify transaction rollback on error (e.g., mock a failure halfway).

## Definition of Done

- [ ] `AutorouteTool` accepts `apply` flag.
- [ ] `apply=True` updates the database correctly.
- [ ] Transactional integrity is ensured.
- [ ] Notification hooks are in place.

## Activity Log

- 2026-01-21T12:08:34Z – Antigravity – shell_pid=4061897 – lane=doing – Started implementation via workflow command
- 2026-01-21T14:00:33Z – Antigravity – shell_pid=4061897 – lane=for_review – Implemented Autoroute apply logic with transactional DB updates and notification hooks. Fixed RoutingStep schema mismatch.
- 2026-01-21T14:54:43Z – Antigravity – shell_pid=4073129 – lane=doing – Started review via workflow command
- 2026-01-21T15:09:36Z – Antigravity – shell_pid=4073129 – lane=done – Review passed: Autoroute execution logic implemented successfully with transaction support and notification hooks. All tests passed.
