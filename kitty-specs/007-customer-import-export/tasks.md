# Tasks: 007 Customer Import Export

**Branch**: `007-customer-import-export` | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)
**Status**: `[ ]` Not Started | `[/]` In Progress | `[x]` Completed

## Work Package 01: Infrastructure & Data Models

**Goal**: Establish the database schema, install dependencies, and create the service skeleton for data management.
**Priority**: P0 (Foundational)
**Dependencies**: None

- [x] **T001**: Install and configure `pandas`, `openpyxl`, and `python-multipart`. Update `requirements.txt`.
- [x] **T002**: Define `ImportJob` SQLAlchemy model (tracking upload status, results, file URL).
- [x] **T003**: Define `ExportRequest` SQLAlchemy model (tracking query, status, result URL).
- [x] **T004**: Generate and apply Alembic migrations for new models.
- [x] **T005**: Create `DataManagementService` class skeleton in `src/services/data_management.py`.

## Work Package 02: Smart Data Import Logic

**Goal**: Implement robust file parsing, intelligent header mapping, and atomic database import.
**Priority**: P1 (Core Value)
**Dependencies**: WP01

- [x] **T006**: Implement `DataManagementService.parse_file` to handle CSV, Excel, and JSON into a pandas DataFrame.
- [x] **T007**: Implement "Smart Header Mapping" to normalize column names (e.g. "Client Name" -> "name").
- [x] **T008**: Implement atomic import logic: validate rows, update existing customers, add jobs. Rollback on failure.
- [x] **T009**: Write unit tests for `parse_file` and `import_data` logic using mocked files.

## Work Package 03: Natural Language Export Logic

**Goal**: Enable users to export data by describing what they want in plain English.
**Priority**: P1 (Core Value)
**Dependencies**: WP01

- [x] **T010**: Create `ExportQueryTool` (or extend `LLMParser`) to translate NL queries into structured filters (JSON).
- [x] **T011**: Implement `DataManagementService.process_export` to query DB, apply filters, and generate CSV/Excel files.
- [x] **T012**: Integrate `S3Service` (or local fallback) to store exported files and generate downloadable URLs.
- [x] **T013**: Write unit and integration tests for the export flow.

## Work Package 04: WhatsApp Interface Integration

**Goal**: Expose the import/export functionality via a dedicated "Data Management" conversation state.
**Priority**: P2 (User Interface)
**Dependencies**: WP02, WP03

- [x] **T014**: Update `ConversationStatus` enum to include `DATA_MANAGEMENT` state.
- [x] **T015**: Implement state transition logic (Entry via command, Exit via "back" or "exit").
- [x] **T016**: Handle file uploads in `DATA_MANAGEMENT` state -> trigger `ImportJob`.
- [x] **T017**: Handle text messages in `DATA_MANAGEMENT` state -> trigger `ExportRequest`.
- [x] **T018**: Verify end-to-end flow with integration tests or manual verification script.
