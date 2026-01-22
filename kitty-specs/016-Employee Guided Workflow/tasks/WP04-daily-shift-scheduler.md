---
work_package_id: "WP04"
title: "Daily Shift Scheduler"
lane: "doing"
subtasks: ["T013", "T014", "T015", "T018"]
dependencies: ["WP03"]
agent: "Antigravity"
shell_pid: "215012"
---

## Objective

Implement the "Morning Overview" capability. A background scheduler will run daily to find employees starting their shift and proactively send them a summary of their day's route.

## Context

User Story 1: "As a Field Employee, I want to receive a summary of my day's work..."
This requires `apscheduler` (installed in WP01) running in the background.

- **Spec**: `kitty-specs/016-Employee Guided Workflow/spec.md`
- **Research**: `kitty-specs/016-Employee Guided Workflow/research.md` (See Section 1 & 3)

## Subtasks

### T013: Implement `SchedulerService`

**Purpose**: Wrapper around `APScheduler` to manage jobs.
**Steps**:

1. Create `src/services/scheduler.py`.
2. Initialize `AsyncIOScheduler`.
3. Create method `start()` and `stop()`.
4. Create method `add_daily_job(func, hour, minute)`.

### T014: Implement `ShiftStarterTask`

**Purpose**: The actual logic to run at 06:30.
**Steps**:

1. In `src/services/scheduler.py` (or `src/tasks/shift_starter.py` if preferred), implement `check_shifts()`:
   - Identify current time (handle UTC conversion if needed).
   - Find employees who should receive a notification now (e.g., simplistic "everyone at 06:30 local" or specific `shift_start` times).
   - For each employee:
     - Fetch today's jobs (using `JobRepository`).
     - Generate summary text (list of jobs, route overview).
     - Call `MessagingService.enqueue_message(employee.phone, summary)`.

### T015: Register in Main Application

**Purpose**: Start the scheduler when the app starts.
**Steps**:

1. Open `src/main.py`.
2. In the `lifespan` context manager:
   - `scheduler_service.start()`.
   - Add the `check_shifts` job (e.g., every 15 mins or fixed cron time).
3. Ensure graceful shutdown (`scheduler_service.stop()`).

### T018: Integration Test

**Purpose**: Verify the scheduler triggers and sends messages.
**Steps**:

1. Create `tests/integration/test_scheduler_flow.py`.
2. Use a mock for `MessagingService`.
3. Manually trigger the `check_shifts` function (don't wait for real time).
4. Assert that `MessagingService.enqueue_message` was called for an employee with jobs.

## Definition of Done

- Application logs show scheduler starting.
- `check_shifts` logic correctly identifies employees and jobs.
- `MessagingService` receives the correct payloads.
- **Note**: Actual timezone handling can be basic (MVP) but code should acknowledge where the complexity lies.

## Activity Log

- [INIT] Task generated.
- 2026-01-21T18:04:16Z – Antigravity – shell_pid=4186310 – lane=doing – Started implementation via workflow command
- 2026-01-21T18:10:40Z – Antigravity – shell_pid=4186310 – lane=for_review – Ready for review: Implemented SchedulerService, background task for daily job summary, integration in main.py, and added integration tests.
- 2026-01-21T18:12:41Z – Antigravity – shell_pid=4186310 – lane=doing – Started implementation via workflow command
- 2026-01-21T18:19:20Z – Antigravity – shell_pid=4186310 – lane=for_review – Ready for review: Implemented SchedulerService, background task for daily job summary, integration in main.py, and added integration tests.
- 2026-01-22T12:03:32Z – Antigravity – shell_pid=215012 – lane=doing – Started review via workflow command
