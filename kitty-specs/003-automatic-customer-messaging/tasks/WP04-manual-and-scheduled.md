---
work_package_id: WP04
subtasks:
  - T011
  - T012
lane: "doing"
agent: "Antigravity"
---

# Work Package 04: Manual & Scheduled Triggers

## Goal

Implement the "On My Way" manual trigger and the "Daily Schedule" automated check.

## Context

These are additional triggers beyond the standard job lifecycle.

## Subtasks

### T011: Implement "On My Way" trigger

- **UI/Interface**: Add a way for the user to trigger this (e.g. a specific chat command or a function tool).
- **Backend**: Emit `OnMyWayEvent(customer_id, eta)`.
- **Handler**: `MessagingService.handle_on_my_way` sends "Technician is on the way..."

### T012: Implement Daily Schedule runner

- **Description**: A scheduled task (cron or simple async loop) that checks for jobs scheduled "today".
- **Logic**:
  - Query jobs scheduled for `date.today()`.
  - For each, emit `JobScheduledTodayEvent` (or reuse Scheduled event with specific flag).
  - Or directly send reminders.
- **Timing**: Run once a day (e.g. 8 AM).

## Verification

- Trigger "On My Way" and verify message.
- Mock the date/time and run the Daily Schedule checker, verify messages sent for jobs on that day.

## Activity Log

- 2026-01-15T20:58:40Z – Antigravity – lane=doing – Started implementation
