---
work_package_id: WP02
subtasks:
  - T006
  - T007
  - T008
  - T009
lane: planned
history:
  - date: 2026-01-17
    action: created
    agent: Antigravity
---

# Work Package 02: Smart Data Import Logic

## Objective

Implement robust file parsing, intelligent header mapping, and atomic database import.

## Context

Core logic for importing customer data. Needs to handle various file formats (CSV, Excel) and messy headers. Must be transactional to prevent partial data corruption.

## Subtasks

### T006: Implement parse_file

- **File**: `src/services/data_management.py`
- **Method**: `async def parse_file(self, file_path_or_buffer: str | BinaryIO, format: str) -> pd.DataFrame`
- **Details**:
  - Use `pandas.read_csv` for CSV.
  - Use `pandas.read_excel` for XLSX.
  - Use `pandas.read_json` for JSON.
  - Standardize DataFrame: strip whitespace from strings, handle NaN.

### T007: Smart Header Mapping

- **Action**: Implement logic to map user headers to internal schema (`name`, `phone`, `email`, `address`, etc.).
- **Strategy**:
  - Simple normalization first: lowercase, snake_case.
  - Mapping dictionary: `{'client_name': 'name', 'mobile': 'phone', ...}`.
  - (Optional) Use LLM if simple mapping fails: sending sample headers to LLM to get a JSON map back. *Start with regex/fuzzy matching first.*

### T008: Atomic Import Logic

- **Method**: `async def import_data(self, df: pd.DataFrame)`
- **Logic**:
  - Start `session.begin_nested()`.
  - Iterate rows.
  - Validate data (e.g. phone number format).
  - Check if Customer exists (by phone/email).
    - If yes: Update attributes.
    - If no: Create `Customer`.
  - If job info present (e.g. `service_type`, `status` columns), create `Job` linked to Customer.
  - Catch exceptions -> Rollback entire transaction.

### T009: Testing

- **Action**: Create `tests/test_data_import.py`.
- **Cases**:
  - Happy path: CSV with perfect headers.
  - Dirty data: Mapped headers ("Client Name").
  - Rollback: One bad row causes 0 DB writes.
  - Updates: Re-importing existing customer updates their fields.

## Definition of Done

- `DataManagementService` can ingest a file and populate `Customer`/`Job` tables.
- Transactional integrity verified by test (1 error = 0 commits).
- Tests pass.

## Risks

- Memory usage for large files: Consider chunking if file > 10MB (pandas chunksize).
- Ambiguous headers: Ensure we don't overwrite data if mapping is unsure.
