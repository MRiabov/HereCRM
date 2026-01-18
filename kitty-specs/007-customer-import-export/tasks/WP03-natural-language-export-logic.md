---
work_package_id: WP03
subtasks:
  - T010
  - T011
  - T012
  - T013
lane: "done"
review_status: "approved without changes"
reviewed_by: Antigravity
agent: "antigravity"
history:
  - date: 2026-01-17
    action: created
    agent: Antigravity
  - date: 2026-01-18
    action: approved
    agent: Antigravity
    note: "NL filter parsing and export formats verified."
---

# Work Package 03: Natural Language Export Logic

## Objective

Enable users to export data by describing what they want in plain English.

## Context

Users want to ask "Export all jobs from last week" and get a CSV. This requires interpreting the NL query into a structured DB filter, executing it, and formatting the result.

## Subtasks

### T010: ExportQueryTool / LLM Parser

- **File**: `src/uimodels.py` or `src/llm_client.py`
- **Action**: Define a tool/function definition `ExportFilter` for the LLM.
- **Schema**:
  - `date_range`: {start, end}
  - `status`: list[str]
  - `city`: str
  - `min_jobs`: int
- **Integration**: Ensure `LLMParser` can produce this structure from a prompt.

### T011: Process Export

- **File**: `src/services/data_management.py`
- **Method**: `async def process_export(self, request_id: int)`
- **Logic**:
  - Fetch `ExportRequest` by ID.
  - Call LLM to parse `query_text` -> `export_filters`.
  - Build SQLAlchemy query based on filters.
  - Execute query -> Get objects.
  - Convert to list of dicts/DataFrame.
  - Write to buffer (CSV/Excel/JSON based on request).

### T012: S3/Storage Integration

- **Logic**:
  - Use `S3Service.upload_file` (from Spec 006) to upload the generated report.
  - Generate a presigned URL (valid for X hours).
  - Update `ExportRequest.file_url` and `status=COMPLETED`.

### T013: Testing

- **Action**: Create `tests/test_data_export.py`.
- **Cases**:
  - "Export all customers" -> Checks count.
  - "Export customers in Dublin" -> Checks filter.
  - Verify file generation (content matches DB).

## Definition of Done

- Users can input text and get a valid URL to a file containing the filtered data.
- System handles basic filters (time, location, status).

## Risks

- LLM Hallucination: It might invent filters we don't support. Default to 'all' or ask for clarification? (Start with best-effort mapping).
- Large exports: 10k rows might be slow. Add limit?

## Activity Log

- 2026-01-17T21:05:22Z – antigravity – shell_pid= – lane=for_review – Already implemented and verified by tests.
