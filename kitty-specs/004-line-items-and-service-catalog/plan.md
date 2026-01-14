# Implementation Plan: Line Items & Service Catalog

**Branch**: `004-line-items-and-service-catalog` | **Date**: 2026-01-14 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/004-line-items-and-service-catalog/spec.md`

## Summary

Implement a **Service Catalog** and **Line Item** system for the WhatsApp CRM.

1. **Catalog Management**: Admin users can manage a list of `Services` (name, default price) via a new `SETTINGS` chat state and menu.
2. **Line Item Inference**: When creating jobs, the system intelligently parses input to infer line items, using catalog defaults to calculate missing quantities or prices (e.g., "$50 total" + "$5/unit default" = "10 units").
3. **Data Persistence**: New `Service` and `LineItem` tables in the existing database.

## Technical Context

**Language/Version**: Python 3.12+ (Existing)
**Primary Dependencies**: `sqlalchemy` (ORM), `openai` (Inference logic)
**Storage**: SQLite/PostgreSQL (SQLAlchemy models)
**Testing**: `pytest`
**Architecture**: Monolithic FastAPI backend + WhatsApp Bot

## Constitution Check

*Skipped: No constitution file found.*

## Project Structure

### Source Code

```
src/
├── models.py             # [MODIFY] Add Service and LineItem tables. Update Job.
├── repositories.py       # [MODIFY] Add ServiceRepository. Update JobRepository.
├── services/
│   ├── whatsapp_service.py # [MODIFY] Add SETTINGS state handler.
│   └── chat_utils.py     # [NEW] Helper for generic menu rendering
├── llm_client.py         # [MODIFY] Update AddJobTool schemas/system prompt
└── assets/
    └── messages.yaml     # [MODIFY] Add Settings/Service templates
```

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| New `Service` Entity | Need to store configurable defaults for catalog | Hardcoding in Python/Config means redeploy to change prices |
| `LineItem` Table | Need distinct accounting entries | Storing as JSON blob in Job prevents easy SQL analytics later |
| New State `SETTINGS` | Need safe mode for admin changes | Doing it in main chat risks accidental "Add service" commands being interpreted as "Add Job" |

## Parallel Work Analysis

N/A - Single stream execution.
