# Implementation Plan: 003 Automatic Customer Messaging

*Path: [templates/plan-template.md](templates/plan-template.md)*

**Branch**: `003-automatic-customer-messaging` | **Date**: 2026-01-14 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/spec-kitty.plan` command. See `.kittify/templates/commands/plan.md` for the execution workflow.

The planner will not begin until all planning questions have been answered—capture those answers in this document before progressing to later phases.

## Summary

### Goal

Enable automated customer messaging via WhatsApp/SMS triggered by business events (Job Created, Scheduled, On My Way).

### Approach

- **Architecture**: Event-driven architecture using the shared internal `EventBus` (`src/events.py`).
- **Queue**: Python `asyncio.Queue` for non-persistent message dispatching.
- **Provider**: Meta Cloud API for WhatsApp messaging.
- **Scope**: "On My Way", "Job Booked", "Job Scheduled", "Daily Schedule", "Smart Follow-up" (Quote 48h), "Review Request" (Job Paid 2h).
- **Automation**: Use a background task or scheduler (e.g., `asyncio` sleep or a more robust scheduler if available) to handle delayed triggers.
- **LLM**: Use the existing OpenAI/LLM service to draft follow-up messages.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: FastAPI, SQLAlchemy, aiosqlite, openai, requests, httpx
**Storage**: SQLite (via aiosqlite)
**Testing**: pytest, pytest-asyncio
**Target Platform**: Linux server
**Project Type**: Single project
**Performance Goals**: N/A
**Constraints**: Sync with internal event bus, non-persistent queue for iteration 1
**Scale/Scope**: Feature level (Messaging subsystem)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

*Constitution file not found. Skipping constitution check.*

## Project Structure

### Documentation (this feature)

```markdown
kitty-specs/[###-feature]/
├── plan.md              # This file (/spec-kitty.plan command output)
├── research.md          # Phase 0 output (/spec-kitty.plan command)
├── data-model.md        # Phase 1 output (/spec-kitty.plan command)
├── quickstart.md        # Phase 1 output (/spec-kitty.plan command)
├── contracts/           # Phase 1 output (/spec-kitty.plan command)
└── tasks.md             # Phase 2 output (/spec-kitty.tasks command - NOT created by /spec-kitty.plan)
```

### Source Code (repository root)

```markdown
src/
├── services/            # MessagingService (updates), CRMService (add JOB_SCHEDULED)
├── models/              # (Updates if needed, though likely minimal for this phase)
├── cli/                 # (Updates if needed)
├── events.py            # SHARED: User existing EventBus from main
└── lib/                 # WhatsAppClient (via requests/httpx)

tests/
├── unit/                # Unit tests for MessagingService integration with EventBus
└── integration/         # Integration tests with mocked WhatsApp API
```

**Structure Decision**: Standard single project structure extending existing `src/`.

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
| :--- | :--- | :--- |
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
