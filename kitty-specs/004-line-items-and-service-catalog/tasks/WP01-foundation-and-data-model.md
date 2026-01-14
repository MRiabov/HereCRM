---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
title: "Foundation & Data Model"
phase: "Phase 1 - Foundational Platform"
lane: "for_review"
assignee: ""
agent: "antigravity"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-14T19:10:01Z"
    lane: "planned"
    agent: "antigravity"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – Foundation & Data Model

## Objectives & Success Criteria

- Establish the core database schema for the Service Catalog and Line Items.
- Ensure efficient data access via dedicated Repositories.
- Enable backward compatibility for existing Jobs while transitioning to line-item-based valuations.

## Context & Constraints

- Follow the architecture in `plan.md` and the schema in `data-model.md`.
- `Service` and `LineItem` models must be implemented using SQLAlchemy.
- `Job.value` should be kept in sync with the sum of its line items for legacy support and performance.

## Subtasks & Detailed Guidance

### Subtask T001 – Implement `Service` model

- **Purpose**: Create the catalog entity.
- **Steps**:
  - Add `Service` class to `src/models.py`.
  - Fields: `id`, `business_id`, `name`, `description`, `default_price`, `created_at`.
- **Files**: `src/models.py`
- **Parallel?**: No

### Subtask T002 – Implement `LineItem` model and update `Job`

- **Purpose**: Create the job-specific charge entity.
- **Steps**:
  - Add `LineItem` class to `src/models.py`.
  - Fields: `id`, `job_id`, `description`, `quantity`, `unit_price`, `total_price`, `service_id`.
  - Update `Job` model with a relationship to `LineItem`s.
- **Files**: `src/models.py`
- **Parallel?**: No

### Subtask T003 – Create database migration

- **Purpose**: Apply schema changes to the database.
- **Steps**:
  - Generate a new migration file (alembic or manual script depending on project setup).
  - Ensure tables are created with proper constraints.
- **Files**: `migrations/` (or equivalent)
- **Parallel?**: Yes

### Subtask T004 – Implement `ServiceRepository`

- **Purpose**: Provide CRUD access for services.
- **Steps**:
  - Implement `ServiceRepository` in `src/repositories.py`.
  - Include methods for `add`, `get_by_id`, `get_all_for_business`, `update`, and `delete`.
- **Files**: `src/repositories.py`
- **Parallel?**: Yes

### Subtask T005 – Update `JobRepository`

- **Purpose**: Handle line item persistence during job workflows.
- **Steps**:
  - Update `JobRepository.save` (or equivalent) to persist associated line items.
  - Implement a signal or hook to update `Job.value` whenever line items change.
- **Files**: `src/repositories.py`
- **Parallel?**: No

## Risks & Mitigations

- Migration drift: Ensure the migration is tested against a clean database.
- Performance: Ensure efficient loading of line items with jobs (use joined loads where appropriate).

## Definition of Done Checklist

- [ ] All subtasks completed and validated
- [ ] Database migration applies successfully
- [ ] Unit tests for models and repositories pass
- [ ] Documentation updated

## Activity Log

- 2026-01-14T19:10:01Z – antigravity – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-14T19:15:36Z – antigravity – lane=doing – Started implementation
- 2026-01-14T19:20:56Z – antigravity – lane=for_review – Ready for review
