# Feature Specification: Customer Data Import & Export

**Feature Branch**: `007-customer-import-export`
**Created**: 2026-01-17
**Status**: Draft
**Input**: User description: "Implement customer import and export functionality with a dedicated screen. Key features: LLM-powered natural language export queries, flexible import parsing with strict validation (preferring imported data for duplicates), support for CSV/JSON/Excel formats, and smart header mapping. Imports should include customer details and associated jobs. Safety mechanisms must prevent database corruption."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Smart Data Import (Priority: P1)

Users need to bulk import customer and job data from various legacy formats (CSV, Excel, JSON) with different column names, without manually reformatting their files.

**Why this priority**: Essential for onboarding new users who bring data from other systems. Reduces friction and manual data entry.

**Independent Test**: Provide a CSV with non-standard headers (e.g., "Client Name" instead of "name") and verify the system correctly maps and imports the data without errors.

**Acceptance Scenarios**:

1. **Given** a CSV file with "Client Phone" and "Client Name" headers, **When** user uploads it for import, **Then** system intelligently maps these to "phone" and "name" and imports records.
2. **Given** an import file contains a customer that already exists (match by phone/email), **When** import functions runs, **Then** system updates the existing customer details with new data and adds any new jobs from the file.
3. **Given** a malformed file (e.g., missing required fields for some rows), **When** user attempts import, **Then** system rejects the *completely* and provides specific error feedback.

---

### User Story 2 - Natural Language Data Export (Priority: P1)

Users need to export specific subsets of their data for reporting or external use by describing what they want in plain English.

**Why this priority**: Empowers non-technical users to access their data without constructing complex database queries.

**Independent Test**: Request "Export all customers with pending jobs from last month" and verify the resulting CSV/Excel file contains exactly those records.

**Acceptance Scenarios**:

1. **Given** a request "Export customers in Dublin added last week", **When** user submits export request, **Then** system generates a downloadable file with only matching customers and their data.
2. **Given** a request specifies "as JSON", **When** export is generated, **Then** the file format is valid JSON.

---

### User Story 3 - Dedicated Data Management Screen (Priority: P2)

Users need a safe, dedicated area to perform these sensitive bulk operations to strictly separate them from daily operational workflows.

**Why this priority**: Prevents accidental data modification and reduces UI clutter on the main dashboard.

**Independent Test**: Navigate to the new "Data Management" route and verify access to Import/Export tools.

**Acceptance Scenarios**:

1. **Given** the user is on the dashboard, **When** they navigate to "Data Management", **Then** they see clear options for "Import" and "Export" with recent history or logs.

---

## Edge Cases

- **Large File Imports**: System should enforce reasonable file size limits (e.g., 20MB) to prevent timeouts.
- **Ambiguous Header Mapping**: If LLM cannot confidently map headers, the system should prompt the user for clarification or fail safely rather than guessing wrong.
- **Partial Failures**: Import MUST be atomic. If row 99 of 100 fails validation, the entire batch of 100 MUST be rolled back.
- **Export Volume**: If an export query matches >10,000 records, system should warn the user or stream the response to prevent memory exhaustion.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a dedicated "Data Management" view separate from the main dashboard.
- **FR-002**: System MUST support importing data from CSV, JSON, and Excel (.xlsx) formats.
- **FR-003**: System MUST use an LLM to analyze upload file headers and map them to the internal `Customer` and `Job` schema.
- **FR-004**: Import process MUST be atomic; if any record in a batch creates a validation error, the entire batch is rejected.
- **FR-005**: System MUST automatically create new `Customer` records if they do not exist.
- **FR-006**: System MUST update existing `Customer` records (matched by unique identifier like phone/email) with imported data (overwrite) and append new `Job` records.
- **FR-007**: System MUST support Natural Language querying for exports (e.g., "Export customers with completed jobs").
- **FR-008**: System MUST support exporting to CSV, JSON, and Excel formats.
- **FR-009**: System MUST validate strict data integrity types (e.g., dates are valid dates, prices are non-negative) before attempting database write.

### Key Entities

- **ImportJob**: Represents a bulk import attempt (Status: Pending, Processing, Completed, Failed; Logs).
- **ExportRequest**: Represents a user's request to extract data (Query, Format, Status).
- **DataMapping**: The schema map generated by the LLM (Source Column -> Target Field).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 95% of standard CSV imports with non-matching but semantically similar headers are mapped correctly without user intervention.
- **SC-002**: 100% of invalid imports result in zero database changes (Atomic Transaction guarantee).
- **SC-003**: Users can successfully filter export data using natural language queries with 90% intent accuracy.
- **SC-004**: System handles files up to 10MB or 5000 records within 30 seconds.
