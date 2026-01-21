---
work_package_id: "WP01"
title: "Foundation & Service Reminders"
lane: "doing"
subtasks: ["T001", "T002", "T003", "T004", "T005", "T006"]
dependencies: []
agent: "Antigravity"
shell_pid: "4074288"
---

## Objective

Establish the foundation for the Employee Guided Workflow by adding service reminder support to the data model and installing the necessary scheduler dependency.

## Context

We need to allow business owners to attach "reminder text" (e.g., "Ask about interior window cleaning") to service types. This text will be used later to nudge employees during their workflow. We also need `apscheduler` for the upcoming morning route overviews.

- **Spec**: `kitty-specs/016-Employee Guided Workflow/spec.md`
- **Plan**: `kitty-specs/016-Employee Guided Workflow/plan.md`
- **Data Model**: `kitty-specs/016-Employee Guided Workflow/data-model.md`

## Subtasks

### T001: Run database migration

**Purpose**: Add `reminder_text` column to the `services` table.
**Steps**:

1. Run `alembic revision -m "add_service_reminder_text"`.
2. In the migration file, add a `reminder_text` column of type `sa.Text()` to the `services` table.
3. Run `alembic upgrade head`.

### T002: Install APScheduler

**Purpose**: Add the background scheduling library.
**Steps**:

1. Run `pip install apscheduler`.
2. Update `requirements.txt` to include `apscheduler`.

### T003: Update Service model

**Purpose**: Reflect the new database field in the SQLAlchemy model.
**Steps**:

1. Update `Service` class in `src/models.py`.
2. Add `reminder_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)`.

### T004: Update ServiceRepository

**Purpose**: Ensure the repository layer handles the new field.
**Steps**:

1. Check `src/repositories/*.py` (likely `job_repository.py` or a dedicated `service_repository.py`).
2. Verify that `create` and `update` methods for services include the `reminder_text` field.

### T005: Update UI Models

**Purpose**: Update Pydantic models for the LLM tools.
**Steps**:

1. Open `src/uimodels.py`.
2. Add `reminder_text: Optional[str] = Field(None, description="...")` to `AddServiceTool` and `EditServiceTool`.

### T006: Update Service Executors

**Purpose**: Ensure tool execution saves the reminder text.
**Steps**:

1. Update `src/tool_executor.py`.
2. Modify `_execute_add_service` and `_execute_edit_service` to pass `reminder_text` to the repository/service layer.

## Definition of Done

- Database has `reminder_text` column.
- `apscheduler` is in `requirements.txt`.
- Services can be created/edited with reminder text via the chat interface.
- Verified by checking the database after an "Edit service" command.

## Activity Log

- [INIT] Task generated.
- 2026-01-21T16:28:01Z – Antigravity – shell_pid=4074288 – lane=doing – Started implementation via workflow command
