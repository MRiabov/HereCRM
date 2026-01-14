# Implementation Plan: Pipeline Progression Logic

**Branch**: `002-pipeline-progression` | **Date**: 2026-01-14 | **Spec**: [.worktrees/002-pipeline-progression/kitty-specs/002-pipeline-progression/spec.md](file:///home/maksym/Work/proj/HereCRM/.worktrees/002-pipeline-progression/kitty-specs/002-pipeline-progression/spec.md)
**Input**: Feature specification from `.worktrees/002-pipeline-progression/kitty-specs/002-pipeline-progression/spec.md`

**Note**: This template is filled in by the `/spec-kitty.plan` command. See `.kittify/templates/commands/plan.md` for the execution workflow.

The planner will not begin until all planning questions have been answered—capture those answers in this document before progressing to later phases.

## Summary

This feature implements an automatic customer pipeline with stages (`Not Contacted`, `Contacted`, `Converted Once`, `Converted Recurrent`, etc.). It utilizes a new `EventBus` to decouple stage progression logic (e.g., job creation triggering stage updates) and updates the core `Customer` model with a `pipeline_stage` Enum. It also adds text-based pipeline querying and filtering capabilities.

## Technical Context

**Language/Version**: Python 3.12 (assumed from existing project)
**Primary Dependencies**: FastAPI, Pydantic, Native Python Enum
**Storage**: In-memory / File-based JSON storage (per existing repositories)
**Testing**: pytest
**Target Platform**: Linux server
**Project Type**: single
**Performance Goals**: <3s response time for pipeline queries
**Constraints**: simple deployment, no external database for now
**Scale/Scope**: Small business CRM, manageable in-memory

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

No constitution file found; section skipped.

## Project Structure

### Documentation (this feature)

```
kitty-specs/002-pipeline-progression/
├── plan.md              # This file
├── research.md          # N/A for this simple feature
├── data-model.md        # To be created
├── quickstart.md        # N/A
├── contracts/           # N/A
└── tasks.md             # To be created
```

### Source Code (repository root)

```
src/
├── models.py            # Update with PipelineStage and Customer field
├── events.py            # NEW: EventBus implementation
├── main.py              # Update: Initialize EventBus
├── services/
│   ├── crm_service.py      # Update: use events, new methods
│   ├── pipeline_handlers.py # NEW: Listeners for stage logic
│   └── whatsapp_service.py # Update: handling new intents
├── llm_client.py        # Update: prompt engineering and tools
└── tests/
    ├── test_pipeline_logic.py # NEW: Core logic tests
    └── test_crm_search.py     # NEW: Search filtering tests
```

**Structure Decision**: Single project structure extending the existing `src/` layout.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| EventBus Pattern | Decouples `Job` creation from `Customer` state logic | Hardcoding `CustomerService` calls inside `JobService` (sic) creates circular dependencies and monolithic service methods. |

## Parallel Work Analysis

N/A - Single developer.
