# Feature Specification: Employee Management Dashboard

**Feature Branch**: `011-employee-management-dashboard`  
**Created**: 2026-01-20  
**Status**: Draft  
**Input**: User description: "Employee management system. We currently have job scheduled for a day, and have employees working between them. Add a screen (see what state machine functionality we have in the system), where an employer can assign jobs to employees, kind of like Jobber and other systems do it. Employees management: John's schedule: 8:00 - job A... Unscheduled jobs: [jobs]. To schedule, say 'Assing #120, 121, 122 to John'..."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Employee Schedule Dashboard (Priority: P1)

As a Business Owner, I want to see a consolidated text view of all my employees' schedules and pending jobs so that I can decide who is available for work this week.

**Why this priority**: this is the core "Screen" requested, enabling decision making. Without visibility, assignment is blind.

**Independent Test**: Can be fully tested by seeding jobs and employees in the DB and verifying the "Show schedule" command output correlates with the data.

**Acceptance Scenarios**:

1. **Given** there are employees with assigned jobs and some unassigned pending jobs, **When** I send "Show schedule" (or similar), **Then** I receive a specific formatted message listing each employee, their jobs sorted by time/sequence, and a list of unassigned jobs at the bottom.
2. **Given** I am a standard member (not owner), **When** I try to view schedule, **Then** I am denied access or ignore.

---

### User Story 2 - Assign Jobs to Employees (Priority: P1)

As a Business Owner, I want to assign specific jobs to specific employees using simple natural language commands like "Assign #123 to John" so that I can distribute work efficiently without complex forms.

**Why this priority**: This is the primary action taken on the dashboard.

**Independent Test**: Can be tested by creating an unassigned job #123 and an employee "John", sending the command, and verifying `job.employee_id` is updated.

**Acceptance Scenarios**:

1. **Given** an unassigned job #101 and employee "Alice", **When** I say "Assign #101 to Alice", **Then** the system replies confirming the assignment and the job is updated in the database.
2. **Given** multiple unassigned jobs (#101, #102), **When** I say "Assign #101 and #102 to Bob", **Then** both jobs are assigned to Bob.
3. **Given** an ambiguous name "John" (two Johns exist), **When** I try to assign, **Then** the system asks for clarification (e.g. "Which John? John A or John B?").

---

### User Story 3 - Reassign/Move Jobs (Priority: P2)

As a Business Owner, I want to move a job from one employee to another or unassign it if plans change.

**Why this priority**: Schedules change frequently; rigidity would make the system unusable.

**Independent Test**: Assign a job to User A, then command "Assign #123 to User B", verify ownership change.

**Acceptance Scenarios**:

1. **Given** Job #101 is assigned to Alice, **When** I say "Assign #101 to Bob", **Then** the job is reassigned to Bob and Alice's schedule no longer shows it.
2. **Given** a job, **When** I say "Unassign #101", **Then** it returns to the "Unscheduled" list.

### Edge Cases

- **Ambiguous Names**: Multiple employees with the same first name. System should prompt or verify.
- **Invalid Job IDs**: User types "#9999" which doesn't exist. System should reply nicely ("Job #9999 not found").
- **Non-Employee Users**: User acts on a valid User ID who is not a 'member' or 'employee'. System should probably allow it but warn, or strictly enforce roles.
- **Completed Jobs**: Assigning a job that is already 'completed'. System should probably block or warn.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST support an `employee_id` association on the `Job` model, querying `User` entities.
- **FR-002**: The `User` model roles MUST differentiate between Owner (Manager) and Employees (Members) to list them in the dashboard.
- **FR-003**: The system MUST implement a "Dashboard View" generator that queries:
  - All Users with 'member'/'employee' role.
  - All Jobs for "today" (or specified date) assigned to those users.
  - All Jobs with status 'pending' (and unassigned) as "Unscheduled".
- **FR-004**: The output format MUST match the user's requested layout:

    ```
    Employees management:
    [Name]'s schedule:
    [Time/Order] - [Description] #[ID] (Location)
    ...
    Unscheduled jobs:
    [Description] #[ID]
    ```

- **FR-005**: The system MUST parse commands matching patterns like "Assign #[ID] to [Name]" or "Move #[ID] to [Name]".
- **FR-006**: This functionality MUST be restricted to Users with `role='owner'`.
- **FR-007**: System MUST expose Dashboard Stats and Recent Activity endpoints for PWA as defined in OpenAPI.

### Key Entities

- **Job**: Modified to include `employee_id` (FK to User) and potentially `scheduled_time` if not present.
- **User**: Used as Employee entity. Filtered by role.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Owners can view the full team schedule in a single message response < 2 seconds.
- **SC-002**: Assignment commands ("Assign #123 to John") are correctly parsed and executed 95% of the time without re-prompting (unless ambiguous).
- **SC-003**: The system successfully handles identical names by prompting for clarification or using unique identifiers.
