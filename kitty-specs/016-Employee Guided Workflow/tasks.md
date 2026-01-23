# Implementation Tasks: Employee Guided Workflow

**Spec**: [016-Employee Guided Workflow](spec.md) | **Status**: Planned

## Overview

This feature provides a convenience layer for field employees, guiding them through their daily tasks via WhatsApp/SMS. It includes a morning overview, navigation links, service-specific reminders, and a quick completion command ("done #123") that automatically pushes the next job details.

## Work Packages

### WP01: Data Layer & Service Config

- **Goal**: Extend the database and management tools to support service-specific reminders.
- **Priority**: High (Blocker)
- **Tests**: Verify `Service` records can store and retrieve `reminder_text`.
- **Subtasks**:
  - [ ] **T001**: Add `reminder_text` to `Service` model and create Alembic migration.
  - [ ] **T002**: Update `ServiceRepository` to support `reminder_text` field in CRUD operations.
  - [ ] **T003**: Update `EditServiceTool` in `uimodels.py` and its executor in `tool_executor.py` to support `reminder_text`.

### WP02: Interactive Job Completion

- **Goal**: Implement the "done" command and the automatic "Push Next Job" logic.
- **Priority**: High
- **Dependencies**: WP01
- **Tests**: End-to-end test of "done #123" command resulting in next job push.
- **Subtasks**:
  - [ ] **T004**: Add `CompleteJobTool` to `uimodels.py` for parsing "done #[ID]" commands.
  - [ ] **T005**: Create a reusable `format_job_details(job)` utility in `src/utils/formatting.py`.
  - [ ] **T006**: Implement `CompleteJobToolExecutor` in `tool_executor.py` (updates status and retrieves next job).
  - [ ] **T007**: Integrate next-job push logic into the completion response.

### WP03: Scheduled Proactive Workflow

- **Goal**: Set up background scheduling to send morning overview messages.
- **Priority**: High
- **Dependencies**: WP02
- **Tests**: Unit test for scheduler logic (mocking time/notifications).
- **Subtasks**:
  - [ ] **T008**: Add `apscheduler` to project dependencies and initialize basic `SchedulerService`.
  - [ ] **T009**: Implement "Shift Start" check and "Morning Overview" notification logic in `SchedulerService`.
  - [ ] **T010**: Register `SchedulerService` in `src/main.py` lifespan and update system prompts for workflow awareness.

### WP04: Daily Shift Scheduler

- **Goal**: Implement the actual scheduling logic for the daily start.
- **Priority**: High
- **Dependencies**: WP03
- **Subtasks**: (See [WP04-daily-shift-scheduler.md](tasks/WP04-daily-shift-scheduler.md))

### WP05: Employee Invitation Flow

- **Goal**: Implement chat-based invitation and onboarding.
- **Priority**: Medium
- **Subtasks**: (See [WP05-employee-invitation-flow.md](tasks/WP05-employee-invitation-flow.md))

### WP06: Promotion and Departure

- **Goal**: Implement role-based promotion, dismissal, and self-departure within management settings.
- **Priority**: Medium
- **Subtasks**: (See [WP06-promotion-and-departure.md](tasks/WP06-promotion-and-departure.md))
