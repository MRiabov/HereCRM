---
work_package_id: WP03
subtasks:
  - T008
  - T009
  - T010
lane: "for_review"
review_status: "approved without changes"
reviewed_by: "antigravity"
agent: "codex"
---

# Work Package 03: Job Lifecycle Events

## Goal

Connect the Job creation and scheduling flows to the Event Bus to trigger automated messages.

## Context

When a job is created or scheduled, the system must emit events so the `MessagingService` can react. This decouples the core domain from messaging.

## Subtasks

### T008: Emit JobBookedEvent from Job creation

- **Location**: `JobRepository.create` or `CRMService.create_job`.
- **Action**: Construct `JobBookedEvent` and call `event_bus.emit(event)`.

### T009: Emit JobScheduledEvent from Job scheduling

- **Location**: Wherever jobs are scheduled (e.g. `JobRepository.update` when `scheduled_at` changes).
- **Action**: Detect change in `scheduled_at`. Construct `JobScheduledEvent` and emit.

### T010: Implement handlers in MessagingService

- **Location**: `src/services/messaging_service.py`
- **Action**:
  - `handle_job_booked(event)`: Formats message "Hi {name}, your job is booked..." -> calls `send_message`.
  - `handle_job_scheduled(event)`: Formats message "Hi {name}, see you on {date}..." -> calls `send_message`.

## Verification

- Create a job via `ToolExecutor` or directly in test.
- Verify `JobBookedEvent` is emitted.
- Verify a `MessageLog` is created for that customer.
- Schedule the job.
- Verify `JobScheduledEvent` is emitted and message logged.

## Activity Log

- 2026-01-15T20:12:26Z – codex – lane=doing – Started implementation
- 2026-01-15T20:31:46Z – codex – lane=for_review – Ready for review
- 2026-01-15T20:45:00Z – antigravity – lane=done – Approved without changes
- 2026-01-16T17:48:06Z – Antigravity – lane=doing – Started implementation
- 2026-01-16T18:11:12Z – codex – lane=for_review – Ready for review
