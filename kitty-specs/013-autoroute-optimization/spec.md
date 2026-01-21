# Feature Specification: Autoroute Optimization

**Feature Branch**: `013-autoroute-optimization`
**Created**: 2026-01-21
**Status**: Draft
**Mission**: software-dev

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run Autoroute Optimization (Priority: P1)

As a Business Owner, I want to automatically generate an optimal schedule for all my employees and pending jobs for a specific day so that travel time is minimized and valid availability windows are respected.

**Why this priority**: Core value proposition of the feature.

**Independent Test**:

1. Setup: 2 Employees (A, B) with start locations.
2. Setup: 4 Jobs (J1-J4) with locations and durations.
3. Action: Run `autoroute today`.
4. Result: System proposes a schedule assigning jobs to A and B with logical geographical grouping.

**Acceptance Scenarios**:

1. **Given** a set of unassigned jobs and available employees, **When** I run `autoroute [date]`, **Then** the system returns a summary of the proposed schedule (Routes, Total Distance, Jobs Assigned).
2. **Given** a customer with availability 10:00-12:00, **When** autoroute runs, **Then** the job is scheduled within that window or left unassigned if impossible.
3. **Given** no solution is found for some jobs, **When** autoroute runs, **Then** those jobs remain in "Unscheduled" list in the preview.

---

### User Story 2 - Confirm and Apply Schedule (Priority: P1)

As a Business Owner, I want to confirm the proposed route so that the jobs are actually assigned and scheduled in the system.

**Why this priority**: Completes the workflow.

**Independent Test**:

1. Run autoroute (preview).
2. Send "Confirmed".
3. Verify database: Jobs have `scheduled_at` and `employee_id` set.

**Acceptance Scenarios**:

1. **Given** a generated preview, **When** I confirm, **Then** all jobs in the proposal are updated in the database.
2. **Given** a confirmation, **When** finished, **Then** the system asks "Do you want to notify customers?" (handoff to Msg Spec).

---

### User Story 3 - Employee Start Locations (Priority: P2)

As a Business Owner, I want to define where each employee starts their day so that routing is accurate.

**Why this priority**: Essential for accurate travel time calculation.

**Acceptance Scenarios**:

1. **Given** an employee User profile, **When** I update their settings, **Then** I can set a `default_start_location` (lat/lng or address).

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST store `availability_windows` on the `Customer` model (list of start/end times per day).
- **FR-002**: The system MUST store `default_start_location` on the `User` model.
- **FR-003**: The system MUST store `estimated_duration` on `Service` (default) and `Job` (override) models.
- **FR-004**: The system MUST implement a `RoutingService` that interfaces with OpenRouteService API (VRP endpoint).
- **FR-005**: The `autoroute [date]` command MUST:
  - Collect all unassigned pending jobs for the target date (or all pending if no date specific, assume target date for execution).
  - Collect all "locked" (already assigned) jobs for that date (as constraints).
  - Collect available employees.
  - Build VRP request payload.
  - Send to ORS.
  - Parse response into a human-readable preview.
- **FR-006**: The system MUST provide a confirmation flow to apply the results to the default DB.

### Key Entities

- **Customer**: Add `availability_windows` (JSON).
- **User**: Add `default_start_location_lat`, `default_start_location_lng`.
- **Job**: Add `estimated_duration` (int, minutes).
- **Service**: Add `estimated_duration` (int, minutes).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Optimization for <50 jobs returns result in <10 seconds.
- **SC-002**: Generated routes respect customer availability windows 100% of the time (or leave job unassigned).
- **SC-003**: "Confirm" action successfully updates all job records atomically.

## Assumptions

- OpenRouteService API key is available in environment variables.
- We trust ORS travel time estimates.
- "Availability" is stored in a simple JSON structure for now (e.g., `[{"start": "09:00", "end": "12:00", "day": "monday"}]` or specific dates? User said "specific time windows... set by business... tommorrow 10am to 12am"). We will store specific datetime ranges or day-of-week recurrence. *Assumption*: For the MVP, we store specific date-time ranges or simple "daily" windows. Let's start with a flexible JSON definition.
