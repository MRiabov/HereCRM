---
work_package_id: "WP01"
title: "Data Model & Core Services"
lane: "doing"
dependencies: []
subtasks: ["T001", "T002", "T003", "T004"]
agent: "Antigravity"
shell_pid: "3779362"
---

# Work Package 01: Data Model & Core Services

## Objective

Establish the database schema foundation and basic service layer for the Employee Management Dashboard. This includes updating the `Job` model to support assignments and creating the services to fetch and manipulate this data.

## Files

- `src/models.py` (Update)
- `src/services/dashboard_service.py` (New)
- `src/services/assignment_service.py` (New)
- `tests/unit/test_services_core.py` (New)

## Detailed Guidance

### T001: Update Job Model

**Purpose**: Store the assignment of a job to an employee.

1. Determine if `src/models.py` uses SQLAlchemy Declarative alignment.
2. Add `employee_id` to the `Job` class:

   ```python
   employee_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
   employee: Mapped[Optional["User"]] = relationship(foreign_keys=[employee_id])
   ```

3. Ensure `scheduled_at` exists or add it.
4. **Verification**: Run `alembic revision --autogenerate` (if alembic is configured) or ensure the app handles schema updates.

### T002: Create DashboardService

**Purpose**: Aggregate data for the main dashboard view.

1. Create `src/services/dashboard_service.py`.
2. Implement `get_employee_schedules(business_id: int, date: date)`:
   - Query all users with roles `member` or `owner` for the business.
   - Query all `jobs` for the given date assigned to these users.
   - Return a structured dict/object: `{employee_obj: [job_list]}`.
3. Implement `get_unscheduled_jobs(business_id: int)`:
   - Query all `jobs` where `employee_id` is None AND status is pending/open.
   - Return a list of jobs.

### T003: Create AssignmentService

**Purpose**: Handle the specific logic of assigning/unassigning.

1. Create `src/services/assignment_service.py`.
2. Implement `assign_job(job_id: int, employee_id: int) -> Job`:
   - Fetch job by ID.
   - Update `job.employee_id`.
   - Commit.
   - Return updated job.
3. Implement `unassign_job(job_id: int) -> Job`:
   - Set `job.employee_id` to None.
   - Commit.

### T004: Unit Tests

**Purpose**: Ensure data layer integrity.

1. Create `tests/unit/test_services_core.py`.
2. Test `assign_job` persists the change.
3. Test `get_employee_schedules` correctly groups jobs by user.
4. Test `get_unscheduled_jobs` only returns unassigned jobs.

## Acceptance Criteria

- `Job` table has `employee_id` column.
- Services can read/write assignments to DB.
- Tests pass.

## Implementation Command

`spec-kitty implement WP01`

## Activity Log

- 2026-01-20T16:18:05Z – Antigravity – shell_pid=3779362 – lane=doing – Started implementation via workflow command
- 2026-01-20T16:27:48Z – Antigravity – shell_pid=3779362 – lane=for_review – Ready for review: BillingService implemented with status retrieval, checkout session creation, and upgrade link generation. Unit tests passing.
- 2026-01-20T16:29:11Z – Antigravity – shell_pid=3779362 – lane=doing – Started review via workflow command
