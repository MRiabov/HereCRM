# Feature Specification: Pipeline Progression Logic

**Feature Branch**: `002-pipeline-progression`
**Created**: 2026-01-14
**Status**: Draft
**Input**: User description: "Implement a CRM pipeline with the following stages: Not Contacted (default for no jobs), Contacted (auto-triggered), Converted Once (1 job), Converted Recurrent (1+ jobs), Not Interested, and Lost. Users should be able to query counts per stage and filter customers by stage in search."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Automatic Pipeline Progression (Priority: P1)

As a CRM user, I want the system to automatically categorize my customers into pipeline stages based on their activity so that I can see the health of my sales funnel without manual updates.

**Why this priority**: Correct automatic categorization is the foundation of the pipeline logic. It ensures data consistency without user overhead.

**Independent Test**: Create a customer without jobs, verify they are "Not Contacted". Create a job for them, verify they become "Converted Once". Create a second job, verify they become "Converted Recurrent".

**Acceptance Scenarios**:

1. **Given** a new customer is added (e.g., "add lead John"), **When** I view the customer details, **Then** their stage is "Not Contacted".
2. **Given** a customer with no jobs, **When** a job is added (e.g., "add John, 50eur"), **Then** their stage automatically updates to "Converted Once".
3. **Given** a customer with one job, **When** another job is added, **Then** their stage automatically updates to "Converted Recurrent".

---

### User Story 2 - Pipeline Querying & Breakdown (Priority: P2)

As a business owner, I want to see a detailed breakdown of my pipeline, including both counts and customer details per stage, so that I can track progress and follow up with specific people.

**Why this priority**: This provides high-level visibility while enabling immediate action on specific customers.

**Independent Test**: Add customers to various stages, then run a query "show me our sales pipeline" and verify it returns a grouped list with customer details (Name, Address, Phone) for each stage.

**Acceptance Scenarios**:

1. **Given** multiple customers across different stages, **When** I ask "how many customers in which pipeline stages" or "show me our sales pipeline", **Then** the system returns a formatted list grouped by stage, showing the count and details (Name, Address, Phone) for customers in that stage.

---

### User Story 3 - Filtering by Stage in Search (Priority: P2)

As a user, I want to filter my customer list by pipeline stage so that I can focus on specific groups like "Leads" or "Lost" customers.

**Why this priority**: Directly requested by the user to improve search utility.

**Independent Test**: Search for "customers in stage Lost" and verify only customers with that status are returned.

**Acceptance Scenarios**:

1. **Given** customers in various stages, **When** I search "show me all Converted Once customers", **Then** only customers in that stage are listed.

---

### User Story 4 - Manual Stage Updates (Priority: P3)

As a user, I want to manually move customers to certain stages like "Not Interested" or "Lost" via natural language.

**Why this priority**: Some stages cannot be inferred automatically (e.g., a customer saying they are not interested).

**Independent Test**: Command "move John to Lost" and verify the stage updates correctly.

**Acceptance Scenarios**:

1. **Given** an active customer, **When** I send "mark John as Not Interested", **Then** their stage is updated to "Not Interested".

### Edge Cases

- **Mixed Automatic/Manual**: If a customer is manually marked as "Lost" but then a job is added, should they move to "Converted Once"? (Assumption: Yes, activity overrides terminal manual statuses unless otherwise specified).
- **Contacted Status**: How is "Contacted" triggered? (Assumption: Any incoming message from the customer or any outgoing message to them that isn't the first interaction).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST maintain a `pipeline_stage` field for each `Customer`.
- **FR-002**: Pipeline stages MUST include: `Not Contacted`, `Contacted`, `Converted Once`, `Converted Recurrent`, `Not Interested`, `Lost`.
- **FR-003**: System MUST set default stage to `Not Contacted` for new customers without jobs.
- **FR-004**: System MUST automatically update stage to `Converted Once` when the first job is created for a customer.
- **FR-005**: System MUST automatically update stage to `Converted Recurrent` when the second or subsequent job is created.
- **FR-006**: System MUST automatically update stage to `Contacted` upon communication interaction (needs concrete definition in implementation).
- **FR-007**: System MUST allow manual stage updates via LLM commands for terminal stages like `Not Interested` and `Lost`.
- **FR-008**: System MUST support querying the pipeline to show counts per stage AND detailed lists of customers (Name, Address, Phone) within each stage.
- **FR-009**: System MUST support filtering customers by `pipeline_stage` in search queries.

### Key Entities

- **Customer**: Updated to include `pipeline_stage` (ENUM or String).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can get a pipeline breakdown in under 3 seconds.
- **SC-002**: 100% of customers are automatically transitioned to "Converted Once" upon their first job creation.
- **SC-003**: Search results accurately filter by stage with 100% precision.
