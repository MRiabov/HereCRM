---
work_package_id: "WP01"
title: "Data Layer & Service Config"
lane: "planned"
subtasks: ["T001", "T002", "T003"]
dependencies: []
---

## Objective

Extend the database and service management tools to support "Service Reminders". This allows business owners to attach specific protocols or upsell nudges to service types, which will later be sent to employees in the guided workflow.

## Context

Employees need to know if there are specific things to do or ask for certain jobs (e.g., "Ask about interior window cleaning" for a "Window Cleaning" job). We need to store this text per service.

- **Spec**: `kitty-specs/016-Employee Guided Workflow/spec.md`
- **Data Model**: `kitty-specs/016-Employee Guided Workflow/data-model.md`

## Subtasks

### T001: Add `reminder_text` to `Service` model and migrations

**Purpose**: Update the `Service` entity to store the optional reminder text.
**Steps**:

1. Open `src/models.py`.
2. Add `reminder_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)` to the `Service` class.
3. Generate a new Alembic migration: `alembic revision -m "add_reminder_text_to_service"`.
4. Verify the migration file in `alembic/versions/` correctly adds the column to the `services` table.

**Files**:

- `src/models.py`
- `alembic/versions/*.py`

### T002: Update `ServiceRepository` for `reminder_text`

**Purpose**: Ensure the data access layer handles the new field for both creation and updates.
**Steps**:

1. Open `src/repositories/service_repository.py`.
2. Locate `create_service` and `update_service` (or equivalent) methods.
3. Ensure they correctly map the `reminder_text` field if provided in the input data.
4. Verify that finding a service by ID or name includes the `reminder_text` in the returned model.

**Files**:

- `src/repositories/service_repository.py`

### T003: Update `EditServiceTool` and its executor

**Purpose**: Allow business owners to configure the reminder text via natural language or the UI.
**Steps**:

1. Open `src/uimodels.py`.
2. Update `EditServiceTool` Pydantic model to include an optional `reminder_text` field.
3. Open `src/tool_executor.py`.
4. Update `_execute_edit_service` (the handler for `EditServiceTool`) to pass the `reminder_text` to the `ServiceRepository`.
5. (Optional) Do the same for `AddServiceTool` if it exists and makes sense to set a reminder on creation.

**Files**:

- `src/uimodels.py`
- `src/tool_executor.py`

## Definition of Done

- [ ] `Service` model has `reminder_text` field.
- [ ] Database schema updated via Alembic.
- [ ] `ServiceRepository` correctly persists `reminder_text`.
- [ ] `EditServiceTool` can be used to set or update the reminder text.
- [ ] Manual test: "Set reminder for Window Cleaning to 'Check if they want screens cleaned'" updates the database correctly.
