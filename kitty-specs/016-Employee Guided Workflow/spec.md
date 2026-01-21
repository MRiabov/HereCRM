# Feature Specification: Employee Guided Workflow

**Feature Branch**: `016-employee-guided-workflow`  
**Created**: 2026-01-21  
**Status**: Draft  
**Input**: User description: "Specification closely related to 011-employee-management-dashboard, except on the employee side. At the beginning of a working day, employees will receive bookings of which jobs they are meant to fulfil for the day, and their route for the day, said as addresses. They will get google maps links to their next location... Shown the name of the customer and their phone number. In addition, a business owner can configure certain reminder for them... As they will start their jobs, they will be prompted 'type XYZ to finish the job'. Basically, a convenience layer for the employees."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Daily Schedule Overlook (Priority: P1)

As a Field Employee, I want to receive a summary of my day's work and planned route when I start my shift so that I can mentally prepare for the day's tasks.

**Why this priority**: it establishes the context for the employee's day and meets the core "morning overlook" requirement.

**Independent Test**: Can be tested by scheduling jobs for an employee and verifying that a summary message is generated with the correct sequence and details.

**Acceptance Scenarios**:

1. **Given** an employee has 3 jobs scheduled for today, **When** the shift starts (or on-demand "Overview"), **Then** the system sends a message listing all 3 jobs in order, including addresses and a calculated route summary.
2. **Given** an employee has no jobs scheduled, **When** the shifts starts, **Then** the system sends a polite message indicating no work is currently assigned.

---

### User Story 2 - Automatic Next Job Guidance (Priority: P1)

As a Field Employee, I want the system to automatically send me the details for my next job as soon as I finish the current one, so that I can transition smoothly without checking a dashboard.

**Why this priority**: This is the core "guided" part of the workflow, reducing friction between jobs.

**Independent Test**: Verify that marking Job #1 as "done" triggers an immediate message containing Job #2's details.

**Acceptance Scenarios**:

1. **Given** I am at Job #101, **When** I send "done #101", **Then** the system replies with: "Job #101 completed. Next stop: [Customer Name] at [Address]. [Map Link]. Customer phone: [Phone]. Reminders: [Service Reminders]."
2. **Given** I just completed my last job of the day, **When** I send "done #[ID]", **Then** the system replies confirming completion and stating that no more jobs are scheduled for the day.

---

### User Story 3 - Service-Specific Reminders & Upsells (Priority: P2)

As a Business Owner, I want to attach specific reminders or "nudges" to different types of services so that my employees are prompted to upsell or follow quality protocols at the right time.

**Why this priority**: Provides business value (upsells/quality) beyond simple coordination.

**Independent Test**: Configure a reminder for "Interior Window Cleaning" and verify it appears in the automated message for projects of that service type.

**Acceptance Scenarios**:

1. **Given** a service "Window Cleaning" has a reminder "Offer interior cleaning for $X", **When** an employee is sent the details for a Window Cleaning job, **Then** the message includes that specific reminder text.
2. **Given** a job has multiple services with different reminders, **When** the job details are sent, **Then** all applicable reminders are listed.

---

### User Story 4 - Quick Job Completion (Priority: P1)

As a Field Employee, I want to complete jobs using a simple text command like "done #123" so that I can record my work quickly and move on.

**Why this priority**: Essential for the proactive workflow to function.

**Independent Test**: Send "done #123" to the system and verify the job status in the database changes to 'completed'.

**Acceptance Scenarios**:

1. **Given** Job #123 is 'assigned' to me, **When** I say "done #123", **Then** the status is updated and I receive a confirmation.
2. **Given** Job #123 is already 'completed', **When** I say "done #123", **Then** the system informs me it's already finished.

---

### Edge Cases

- **Out-of-order Completion**: Employee forgets to finish Job #1 and tries to finish Job #2. System should handle this gracefully (perhaps asking if Job #1 is also done).
- **Missing Geocodes**: If a job address isn't geocoded, the map link should fallback to a standard search link or notify the employee.
- **Multiple Employees**: Ensuring "done #123" only works if the job is actually assigned to the sender.
- **Re-routing**: If the schedule changes mid-day, the "Next Job" logic should reflect the updated sequence.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST implement a "Shift Starter" event that triggers a summary message to assigned employees at their configured shift start time.
- **FR-002**: The system MUST generate Google Maps navigation links (URL) for each job using coordinates if available, or the full address string.
- **FR-003**: The system MUST listen for "done #[ID]" messages and update the corresponding Job status to 'completed'.
- **FR-004**: Upon successful job completion via the text command, the system MUST automatically query for the next 'assigned' but 'pending' job for that employee and push its details.
- **FR-005**: The `Service` entity MUST be extended to store optional "Reminder Text" or "Upsell Prompts".
- **FR-006**: Automated job detail messages MUST include: Customer Name, Address (with Map link), Phone Number (as a clickable tel: link), and all applicable Service Reminders.
- **FR-007**: The system MUST verify that the sender has permission to mark a job as 'done' (i.e., they are the assigned employee or an owner).

### Key Entities

- **Job**: Tracks status, assigned employee, and sequence in the daily route.
- **Service**: Stores "Type" and associated "Reminder/Nudge" text.
- **User (Employee)**: Stores shift start time and preferred communication channel (WhatsApp/SMS).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of employees with scheduled jobs receive their morning overview message automatically.
- **SC-002**: Transition time (from "done" to "next job" details) is under 3 seconds in typical network conditions.
- **SC-003**: Owners can configure or update a service reminder via the management interface and have it active for the next "push" message immediately.
- **SC-004**: System correctly handles `done #[ID]` commands with 99% accuracy for valid IDs.
