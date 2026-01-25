# Implementation Plan: 019-business-workflow-defaults

Path: kitty-specs/019-business-workflow-defaults/plan.md

**Branch**: `019-business-workflow-defaults` | **Date**: 2026-01-22 | **Spec**: [kitty-specs/019-business-workflow-defaults/spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/019-business-workflow-defaults/spec.md`

## Summary

This feature introduces configurable workflow defaults for businesses to tailor HereCRM to their operational needs. Key settings include invoicing, quoting, and payment timing. The technical approach involves a centralized `WorkflowSettingsService`, dynamic help text filtering in `messages.yaml`, and "soft-blocking" with owner overrides in the tool executor.

## Technical Context

**Language/Version**: Python 3.12  
**Primary Dependencies**: SQLAlchemy, Pydantic, FastAPI  
**Storage**: SQLite with SQLAlchemy ORM  
**Testing**: pytest  
**Target Platform**: Linux server
**Project Type**: Single project (Conversational Backend)  
**Performance Goals**: Low latency for tool execution and help text rendering (< 100ms)  
**Constraints**: Settings must be persisted as **strict columns** in the `Business` table (SQLite); RBAC enforcement for settings modification. Avoid JSON fields for core settings.  
**Scale/Scope**: ~8-12 workflow settings and defaults, applied globally per business.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

1. **LLM-First Text Processing**: PASSED. Settings management is conversational; LLM interprets user intent for updates.
2. **Intent Transparency and Control**: PASSED. "Soft-blocking" pattern provides transparency (warning user feature is disabled) and control (owner override).
3. **Progressive Documentation**: PASSED. Plan includes updating `messages.yaml` for dynamic help and `manual.md` for assistant knowledge.

## Project Structure

### Documentation (this feature)

```markdown
kitty-specs/019-business-workflow-defaults/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (generated via /spec-kitty.tasks)
```

### Source Code (repository root)

```bash
src/
├── models.py            # Update Business model with settings
├── database.py          # Migration handling (implicit via SQLAlchemy or Alembic)
├── services/
│   ├── workflow.py      # New WorkflowSettingsService
│   └── crm.py           # Integrity checks and default values
├── tool_executor.py     # Soft-blocking logic
└── assets/
    └── messages.yaml    # Dynamic help templates

tests/
├── integration/         # Workflow enforcement tests
└── unit/                # Settings service tests

### API Exposure
- Expose Workflow Settings endpoints (Get, Update) for PWA.
```

**Structure Decision**: Option 1: Single project. All business logic and models reside in `src/`.

## Complexity Tracking

### Gates Justification

| Violation | Why Needed | Simpler Alternative Rejected Because |
|:----------|:-----------|:-------------------------------------|
| N/A       |            |                                      |
