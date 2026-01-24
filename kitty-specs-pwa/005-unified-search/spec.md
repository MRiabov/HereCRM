# Feature Specification: Advanced Search

**Feature Branch**: `005-unified-search`
**Created**: 2026-01-15
**Updated**: 2026-01-17 (Post-merge of 002, 004)
**Status**: Draft
**Input**: User description: "Implement a central Search functionality in the application. It should use an LLM to automatically identify what is being searched for (job, request, customer) and the fields effectively. support 'detailed' keyword. maintain existing formatting. Handle edge cases. Support Proximity search using OpenStreetMap. It should be a unified SearchService."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Flexible Entity Search (Priority: P1)

Users need to search for Jobs, Customers, or Requests using natural language without specifying the entity type explicitly, allowing for a fluid conversational experience.

**Why this priority**: Core value proposition of "unified" search - removing friction of specific commands.

**Independent Test**: Can be tested by sending varied search queries ("Find John", "Show jobs for John", "Requests about windows") and verifying correct entities are returned.

**Acceptance Scenarios**:

1. **Given** one or more customers named "John Doe" exist, **When** user sends "Find John", **Then** system returns all matching Customer records for John Doe.
2. **Given** one or more jobs associated with "John Doe" exist, **When** user sends "Show jobs for John", **Then** system returns all associated Job records.
3. **Given** one or more requests containing "leaky faucet" exist, **When** user sends "search for leaky faucet", **Then** system returns all matching Request records.

---

### User Story 2 - Proximity Search (Priority: P1)

Users need to find customers or jobs near a specific location or their own location to optimize routing and logistics.

**Why this priority**: High business value for routing and planning field work.

**Independent Test**: Create entities at known locations, run "search within X km of Y", verify inclusion/exclusion.

**Acceptance Scenarios**:

1. **Given** a customer at "High St, Dublin" and one in "Cork", **When** user sends "Show customers within 5km of High St, Dublin", **Then** system returns only the Dublin customer.
2. **Given** a user location is provided (simulated), **When** user sends "Jobs near me", **Then** system uses user location as center point for proximity search.
3. **Given** an invalid address, **When** user searches near it, **Then** system gracefully informs about geocoding failure or suggests correction.

---

### User Story 3 - Detailed View (Priority: P2)

Users need to see full details of a record on demand, while keeping the default view concise to avoid screen clutter.

**Why this priority**: Balances need for quick scanning (concise) with need for deep dive (detailed).

**Independent Test**: Search with and without "detailed" keyword, compare output length/fields.

**Acceptance Scenarios**:

1. **Given** a customer "Jane", **When** user sends "Show Jane", **Then** system returns a concise summary (Name, Phone, maybe Address).
2. **Given** a customer "Jane", **When** user sends "Show Jane detailed", **Then** system returns full record (Name, Phone, Address, Notes, History).

---

### User Story 4 - Complex Filtering (Priority: P3)

Users need to filter by specific attributes like phone number, date, or status.

**Why this priority**: Enhances power user capabilities and precise retrieval.

**Independent Test**: Search by phone substring, date ranges, or status.

**Acceptance Scenarios**:

1. **Given** multiple customers, **When** user searches by partial phone number "085", **Then** system returns all matching customers.
2. **Given** jobs in different statuses, **When** user asks "Show pending jobs", **Then** system returns only jobs with status 'PENDING'.
3. **Given** jobs created on different dates, **When** user asks "Show jobs created last week", **Then** system returns jobs with `created_at` within the last 7 days.
4. **Given** jobs with and without schedules, **When** user asks "Show unscheduled jobs", **Then** system returns jobs where `scheduled_time` is null.
5. **Given** jobs scheduled for various dates, **When** user asks "Show jobs for next month" or "Show jobs on Jan 25th", **Then** system returns jobs with `scheduled_time` matching the parsed date range.
6. **Given** customers in various pipeline stages (from Feature 002), **When** user asks "Show lost customers", **Then** system returns customers with `pipeline_stage == 'lost'`.
7. **Given** a service catalog (from Feature 004), **When** user asks "Search for customers for whom we performed Window Cleaning", **Then** system returns customers for whom we performed those services.
8. **Given** a service catalog (from Feature 004), **When** user asks "Search for jobs for where we performed Window Cleaning", **Then** system returns jobs for those services.

## Edge Cases

- **Large Result Sets**: If "Show all jobs" returns 100 items, system should truncate or paginate to avoid WhatsApp message limits.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST implement a unified `SearchService` that accepts a natural language query string.
- **FR-002**: System MUST use an LLM (via `LLMClient`) to interpret the query intent (Target Entity: Customer/Job/Request/Service/All) and extract filter parameters (Name, Phone, Location, Status, PipelineStage, CreatedAt, ScheduledTime, "Detailed" flag).
- **FR-003**: System MUST support "Proximity Search" by geocoding a reference address (using OpenStreetMap/Nominatim) and filtering entities validation logic (within X km/meters).
- **FR-004**: System MUST support an explicit boolean `detailed` flag in the search context; if true, the output formatter renders extended data (e.g., job line items, full customer notes).
- **FR-005**: System MUST maintain current "concise" formatting (summary view) by default, preserving changes introduced by Feature 002 (stages) and 004 (line items).
- **FR-006**: System MUST return grouped results if multiple entity types match (e.g., "Results for 'John': 1 Customer, 2 Jobs").
- **FR-007**: System MUST handle pagination or truncation for > 10 results to fit WhatsApp constraints.
- **FR-008**: System MUST support searching the Service Catalog specifically (Entity: Service).
- **FR-009**: System SHOULD support searching Message Logs (from Feature 003) if available in the database.

### Key Entities

- **SearchService**: Core domain service handling orchestration.
- **SearchRequest**: Value object representing the parsed intent (target entity, filters, flags).
- **GeocodingService**: (Wrapper around OSM) to convert Address -> Lat/Long.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Proximity searches return results within requested radius with 90% accuracy (dependent on OSM data).
- **SC-002**: "Detailed" view requests trigger full data display 100% of the time.
- **SC-003**: Search queries returning < 5 items render in under 3 seconds.
- **SC-004**: Ambiguous queries (e.g., common names) return results from multiple categories if applicable, rather than failing.
