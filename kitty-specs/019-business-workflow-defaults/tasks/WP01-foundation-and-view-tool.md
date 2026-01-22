---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
title: "Foundation & View Tool"
phase: "Phase 1 - Data Model & Service Foundation"
lane: "planned"
dependencies: []
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-22T08:25:20Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – Foundation & View Tool

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately (right below this notice).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review. If you see feedback here, treat each item as a must-do before completion.]*

---

## Objectives & Success Criteria

- Update the `Business` model to include all workflow-related columns.
- Ensure the database schema is updated via a migration.
- Create a centralized service for managing workflow settings with sensible defaults.
- Implement the `GetWorkflowSettingsTool` so users can view their current state.

### Success Criteria

- [ ] `Business` table has 6 new columns: `workflow_invoicing`, `workflow_quoting`, `workflow_payment_timing`, `workflow_tax_inclusive`, `workflow_include_payment_terms`, `workflow_enable_reminders`.
- [ ] Migration applied successfully.
- [ ] `WorkflowSettingsService` returns default values for businesses where columns are NULL.
- [ ] `GetWorkflowSettingsTool` returns a consistent JSON object representing the state.

## Context & Constraints

- Follow the implementation plan at `kitty-specs/019-business-workflow-defaults/plan.md`.
- Data model details are in `kitty-specs/019-business-workflow-defaults/data-model.md`.
- Contract for tools is in `kitty-specs/019-business-workflow-defaults/contracts/settings.md`.
- Use SQLAlchemy Enums as defined in the data model.
- Defaults:
  - `workflow_invoicing`: `manual`
  - `workflow_quoting`: `manual`
  - `workflow_payment_timing`: `usually_paid_on_spot`
  - `workflow_tax_inclusive`: `True`
  - `workflow_include_payment_terms`: `False`
  - `workflow_enable_reminders`: `False`

## Subtasks & Detailed Guidance

### Subtask T001 – Update Business model in `src/models.py`

- **Purpose**: Add persistence for workflow settings.
- **Steps**:
    1. Import `Enum` from SQLAlchemy or use Python enums with `SAEnum`.
    2. Add columns to `Business` class:
        - `workflow_invoicing`: Enum('never', 'manual', 'automatic')
        - `workflow_quoting`: Enum('never', 'manual', 'automatic')
        - `workflow_payment_timing`: Enum('always_paid_on_spot', 'usually_paid_on_spot', 'paid_later')
        - `workflow_tax_inclusive`: Boolean
        - `workflow_include_payment_terms`: Boolean
        - `workflow_enable_reminders`: Boolean
    3. All columns should be nullable initially to support existing data without immediate mass-update, but the service layer should handle defaults.
- **Files**: `src/models.py`

### Subtask T002 – Create database migration

- **Purpose**: Update physical schema.
- **Steps**:
    1. Generate a new migration script (e.g., using `alembic revision --autogenerate`).
    2. Review the script to ensure it adds the 6 columns correctly.
    3. Apply the migration.
- **Files**: `migrations/versions/*.py`

### Subtask T003 – Implement `WorkflowSettingsService` in `src/services/workflow.py`

- **Purpose**: Provide a clean API for other modules to access business-specific workflow logic.
- **Steps**:
    1. Create `src/services/workflow.py`.
    2. Define a class `WorkflowSettingsService`.
    3. Implement `get_settings(business_id: int)` which returns a Pydantic model or dict with settings, filling in defaults if the DB values are null.
    4. Implement `update_settings(business_id: int, **settings)` (basic persistence).
- **Files**: `src/services/workflow.py`

### Subtask T004 – Implement `GetWorkflowSettingsTool` in `src/tools/settings.py`

- **Purpose**: Allow the conversational agent to retrieve current settings.
- **Steps**:
    1. Implement the tool in `src/tools/settings.py` (follow `contracts/settings.md`).
    2. Use `WorkflowSettingsService` to fetch the data.
    3. Ensure the output is formatted clearly for the LLM.
- **Files**: `src/tools/settings.py`

## Test Strategy

- **Manual Test**: Run `python scripts/check_schema.py` (if it exists) or use a SQL client to verify columns.
- **Unit Test**: Test `WorkflowSettingsService.get_settings` with a mock business that has all NULLs to verify defaults.

## Definition of Done Checklist

- [ ] All subtasks completed and validated
- [ ] `tasks.md` updated with status change
- [ ] `GetWorkflowSettingsTool` works in local testing

## Activity Log

- 2026-01-22T08:25:20Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
