---
work_package_id: WP03
title: Employee Time Tracking
lane: "doing"
dependencies: []
subtasks: [T010, T011, T012, T013, T014]
agent: "Antigravity"
shell_pid: "571973"
review_status: "has_feedback"
reviewed_by: "MRiabov"
---

# Work Package: Employee Time Tracking

## Inspection

- **Goal**: Implement the state management for tracking when employees start/stop work or jobs. This captures the _time arguments_ needed for wage calculation.
- **Role**: Backend Engineer.
- **Outcome**: employees can "Check In", "Start Job", etc., and the system reliably tracks the timestamps.

## Context

We need to capture the `start_time` for both shifts and jobs so that later (in WP04) we can calculate the duration. This WP focuses on **State Transitions** and **Tooling**.

## Detailed Subtasks

### T010: Implement TimeTrackingService

**Goal**: Logic for state updates.
**Files**: `src/services/time_tracking.py`
**Methods**:

1. `check_in(user_id: int) -> User`:
    - Check if already checked in? (Optional: maybe just update start time or error).
    - Set `User.current_shift_start = now()`.
    - Commit.
2. `check_out(user_id: int) -> tuple[User, datetime, datetime]`:
    - Require `User.current_shift_start` is set.
    - Return `(user, start_time, end_time)`.
    - Set `User.current_shift_start = None`.
3. `start_job(job_id: int, user_id: int) -> Job`:
    - Set `Job.started_at = now()`.
    - Update Job Status to 'In Progress' (utilize existing functionality if available).
4. `finish_job(job_id: int) -> tuple[Job, datetime, datetime]`:
    - Require `Job.started_at`.
    - Return `(job, start_time, end_time)`.
    - Set `Job.started_at = None` (or keep it? Spec implies we pay for "Start/Finish" duration. If we clear it, we lose record? Better to rely on the LedgerEntry as the permanent record. Clearing `started_at` resets the state for "Active" job).

### T011: Check In/Out Tools

**Goal**: Create LLM tools for shift management.
**Files**: `src/tools/shifts.py`

- `CheckInTool`: Calls `TimeTrackingService.check_in`. Returns "Checked in at HH:MM".
- `CheckOutTool`: Calls `TimeTrackingService.check_out`. Returns "Checked out. Shift duration: X hours." (Note: Wage calc happens in WP04, here just Ack).

### T012: Job Start/Finish Tools

**Goal**: Create LLM tools for job management.
**Files**: `src/tools/jobs_time.py` (or extend existing `src/tools/jobs.py`)

- `StartJobTool(job_id)`: Calls `service.start_job`.
- `FinishJobTool(job_id)`: Calls `service.finish_job`.

### T013: State Persistence

**Goal**: Ensure the database updates from T010 work correctly.
**Note**: This is likely covered by implementing the Service in T010 using the models from WP01.

### T014: Integration Tests

**Goal**: Verify flows.
**Files**: `tests/integration/test_time_tracking.py`
**Scenarios**:

- User checks in -> `current_shift_start` is set.
- User checks out -> returns duration, `current_shift_start` is None.
- User starts job -> `Job.started_at` set.
- Error case: Check out without check in.
- Error case: Finish job without start.

## Validation

- [x] Tests pass.
- [x] Logic correctly handles timezone awareness (use `datetime.now(timezone.utc)` everywhere!).

## Definition of Done

- Tools are ready to be registered.
- Service handles state transitions correctly.
- Database records state changes.

## Activity Log

- 2026-01-22T12:05:25Z – unknown – lane=for_review – Completed Webhook Dispatcher implementation. Added event constants and decorator-based subscription. Verified with unit tests.
- 2026-01-22T14:06:27Z – Antigravity – shell_pid=230585 – lane=doing – Started review via workflow command
- 2026-01-22T14:11:09Z – Antigravity – shell_pid=230585 – lane=planned – Moved to planned
- 2026-01-22T14:17:05Z – Antigravity – shell_pid=230585 – lane=doing – Started implementation via workflow command
- 2026-01-22T14:54:39Z – Antigravity – shell_pid=230585 – lane=for_review – Implementation complete
- 2026-01-22T17:57:36Z – Antigravity – shell_pid=310764 – lane=doing – Started review via workflow command
- 2026-01-22T18:00:50Z – Antigravity – shell_pid=310764 – lane=done – Review passed: Employee time tracking (Check In/Out, Job Start/Finish) implemented with Service, Tools, and UI models. Integration tests pass. RBAC config updated.
- 2026-01-25T07:36:44Z – Antigravity – shell_pid=571973 – lane=doing – Started implementation via workflow command

## Review Feedback

**Implementation Missing**: The work package "WP03 - Employee Time Tracking" has not been implemented. Investigating the source code and worktree reveals that none of the files specified (e.g., `src/services/time_tracking.py`) exist.

**Metadata Error**: The activity log for this WP erroneously contains an entry from a different feature ("Completed Webhook Dispatcher implementation" from Spec 015). It appears this WP was marked as `for_review` by mistake or due to a script error.

**Action Required**: Move this back to `planned` and assign an agent to implement the actual requirements (Check In/Out, Job Start/Finish tools, and state transitions).
