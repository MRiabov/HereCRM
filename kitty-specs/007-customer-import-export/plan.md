# Implementation Plan: 007 Customer Import Export

*Path: [templates/plan-template.md](templates/plan-template.md)*

**Branch**: `007-customer-import-export` | **Date**: 2026-01-17 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/007-customer-import-export/spec.md`

**Note**: This template is filled in by the `/spec-kitty.plan` command. See `.kittify/templates/commands/plan.md` for the execution workflow.

The planner will not begin until all planning questions have been answered—capture those answers in this document before progressing to later phases.

## Planning Interrogation

### Q1: "Dedicated Data Management Screen" - Web UI or Conversational?

**Context**: The spec asked for a "screen", but the repo is a headless WhatsApp bot.
**Discovery**: User clarified that "screen" refers to a state/mode, similar to the existing "Settings" mode, not a visual web dashboard.
**Decision**: Implement `DATA_MANAGEMENT` as a new state in `ConversationStatus`.
**Impact**:

- No HTML/Jinja2 templates needed.
- No separate Web Auth required.
- New state handler in `WhatsappService`.

### Q2: Authentication Strategy

**Context**: If we built a web UI, we'd need login.
**Decision**: Since we are staying within WhatsApp, we implicitly trust the `from_number` (validated by `verify_signature`).
**Impact**: Reuse existing `AuthService` and `UserRepository` lookup.

### Q3: Data Processing Stack

**Context**: Need to handle CSV and Excel with "smart" mapping.
**Decision**: Use `pandas` for core data frame operations and `openpyxl` for Excel ingest.
**Why**: `pandas` offers superior type inference and data cleaning capabilities compared to raw CSV/XML parsing. It also simplifies the "Natural Language Export" by allowing SQL-like filtering on dataframes if needed (though we will likely filter via ORM for safety).

### Q4: Natural Language Export Safety

**Context**: "Export customers who..."
**Decision**: Map NL queries to structured filters (e.g., `{"city": "Dublin", "min_jobs": 1}`) rather than generating SQL directly.
**Why**: Prevents SQL injection and hallucinated schema attacks.

## Summary

### Goal

Enable bulk import of customer/job data from CSV/Excel/JSON files via WhatsApp, and provide natural language based data export.

### Approach

- **Conversation Mode**: Introduce a `DATA_MANAGEMENT` state in the `ConversationStatus` state machine. This isolates bulk operations from daily CRM usage.
- **Processing**: Use `pandas` and `openpyxl` for robust file parsing and validation.
- **Atomic Import**: Use SQLAlchemy nested transactions to ensure "all-or-nothing" import safety (FR-004).
- **Entities**: New `ImportJob` and `ExportRequest` models to track async operations.
- **API**: Extend `WebhookPayload` to support `media_url` handling for file uploads.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: FastAPI, SQLAlchemy, aiosqlite, pandas, openpyxl, python-multipart
**Storage**: SQLite (via aiosqlite), S3 (reused for exports)
**Testing**: pytest, pytest-asyncio
**Target Platform**: Linux server
**Project Type**: Single project
**Performance Goals**: Support 10MB or 5000 records within 30s
**Constraints**: No web UI - headless WhatsApp flow only
**Scale/Scope**: Feature level (Data Management subsystem)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

*Constitution file not found. Skipping constitution check.*

## Project Structure

### Documentation (this feature)

```
kitty-specs/007-customer-import-export/
├── plan.md              # This file (/spec-kitty.plan command output)
├── research.md          # Phase 0 output (/spec-kitty.plan command)
├── data-model.md        # Phase 1 output (/spec-kitty.plan command)
├── quickstart.md        # Phase 1 output (/spec-kitty.plan command)
├── contracts/           # Phase 1 output (API Contracts)
└── tasks.md             # Phase 2 output (/spec-kitty.tasks command)
```

### Source Code (repository root)

```
src/
├── services/            
│   ├── data_management.py   # [NEW] DataManagementService (pandas logic)
│   ├── parser_datamgmt.py   # [NEW] DataManagementParser (Export tools)
│   └── whatsapp_service.py  # [MODIFY] Add Data Management state handler
├── models.py                # [MODIFY] Add ImportJob, ExportRequest
├── uimodels.py              # [MODIFY] Add ExportQueryTool
├── api/
│   └── routes.py            # [MODIFY] WebhookPayload media support
└── config.py                # No changes anticipated
```

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | | |
