# Research Findings: Customer Import/Export

## Technology Decisions

### 1. Data Processing

**Decision**: Use `pandas` and `openpyxl`.
**Rationale**: `pandas` provides robust handling for CSV/Excel variants, type inference, and data cleaning. It's more reliable than writing custom CSV parsers, especially for "messy" user data. `openpyxl` is required for `.xlsx` support.
**Action**: Add `pandas` and `openpyxl` to `pyproject.toml`.

### 2. File Ingestion via WhatsApp

**Context**: The current `WebhookPayload` only handles text `body`.
**Finding**: WhatsApp Business API (and testing harnesses) typically send `media_url` and `media_type` for file attachments.
**Decision**: Extend `WebhookPayload` to assume these fields are present when a file is sent.
**Security**: The system must validate the `media_type` (allow only csv, xlsx, json) before attempting download.

### 3. Atomic Data Operations

**Requirement**: "All or Nothing" import.
**Mechanism**: SQLAlchemy `AsyncSession` supports transactions.
**Strategy**:

1. Load file into memory (`pandas`).
2. Validate *all* rows against schema.
3. If validation passes, begin a transaction.
4. Upsert customers and jobs.
5. Commit.
6. If any DB error occurs, Rollback.
**Note**: We will not use "batching" in the sense of multiple commits. For < 500 records (limit), a single transaction is performant enough.

## Risks & Mitigations

| Risk | Mitigation |
| :--- | :--- |
| Large file memory exhaustion | Enforce 10MB limit in `DataManagementService`. |
| LLM Hallucinated Mapping | Strict schema validation after LLM mapping. If columns don't match known fields, abort. |
| Timeouts | Use async file IO. If processing > 10s, we might need a background queue (Celery/Arq), but adhering to "Keep It Simple", we will initially process in-request with a reasonable timeout. |
