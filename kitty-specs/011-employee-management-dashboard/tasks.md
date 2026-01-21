# Tasks: Employee Management Dashboard

**Feature Branch**: `011-employee-management-dashboard`
**Status**: Planned

## Work Packages

### WP01: Data Model & Core Services

**Goal**: Update the database schema and implement base service layer for schedule data retrieval and simple assignment.
**Priority**: Critical path
**Dependencies**: None

- [x] **T001**: Update `Job` model in `src/models.py` to include `employee_id` (FK to `users.id`) and `scheduled_at`.
- [x] **T002**: Create `DashboardService` in `src/services/dashboard_service.py` with methods to fetch scheduled jobs (grouped by user) and unscheduled jobs.
- [x] **T003**: Create `AssignmentService` in `src/services/assignment_service.py` with basic `assign_job(job_id, user_id)` and `unassign_job(job_id)` methods.
- [x] **T004**: Create unit tests in `tests/unit/test_services_core.py` to verify data storage and retrieval.

**Implementation Sketch**:

1. Modify `Job` model.
2. Implement schema migration (if applicable) or verify auto-migration.
3. Scaffold service classes.
4. Write tests for basic CRUD operations on assignments.

### WP02: Intelligent Assignment Logic

**Goal**: Implement fuzzy name matching and validation logic to make assignment robust.
**Priority**: High
**Dependencies**: WP01

- [x] **T005**: Implement `find_employee_by_name(name_fragment)` in `AssignmentService` using fuzzy string matching (e.g., Levenshtein or database `ILIKE`).
- [x] **T006**: Add validation to `assign_job`: check if user is a member, check for scheduling conflicts (warn only), ensure job exists.
- [x] **T007**: Create robust unit tests in `tests/unit/test_assignment_logic.py` covering edge cases (ambiguous names, non-existent jobs).

**Implementation Sketch**:

1. Add `thefuzz` or similar lib if needed (or simple SQL `ILIKE`).
2. Enhance `AssignmentService` with lookup logic.
3. Test with scenarios like "Assign to Jon" detecting "John Doe".

### WP03: Dashboard Presentation

**Goal**: Create the text-based view for the dashboard using Jinja2 templates.
**Priority**: Medium
**Dependencies**: WP01

- [x] **T008**: Create Jinja2 template `src/templates/dashboard.txt` matching FR-004 layout.
- [x] **T009**: Implement `render_dashboard(data)` in `src/lib/text_formatter.py` (or service method) that prepares data structs and renders the template.
- [x] **T010**: Verify output format with a test case in `tests/unit/test_presentation.py`.

**Implementation Sketch**:

1. Define the exact text layout in a template file.
2. Build the data-preparation layer (grouping jobs by employee).
3. Render and verify string output.

### WP04: Agent Tools & Integration

**Goal**: Expose functionality to the LLM via Tools and update the agent configuration.
**Priority**: Final
**Dependencies**: WP02, WP03

- [x] **T011**: Create `ShowScheduleTool` and `AssignJobTool` in `src/tools/employee_management.py`.
- [x] **T012**: Wire tools to use `DashboardService` and `AssignmentService` (including handling the fuzzy match results/clarifications).
- [x] **T013**: Register tools in the main `LLMClient` or agent loop configuration.
- [x] **T014**: Create integration test `tests/integration/test_employee_dashboard_flow.py` simulating a full user conversation.

**Implementation Sketch**:

1. Write the Pydantic-based Tool definitions.
2. Implement the `run` methods to call services.
3. Register tools.
4. Run full flow test.
