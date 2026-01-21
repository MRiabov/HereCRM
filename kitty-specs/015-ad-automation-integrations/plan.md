# Implementation Plan: Ad Automation & Integrations

*Path: templates/plan-template.md*

**Branch**: `015-ad-automation-integrations` | **Date**: 2026-01-21 | **Spec**: [015-ad-automation-integrations](spec.md)
**Input**: Feature specification from `/kitty-specs/015-ad-automation-integrations/spec.md`

## Summary

This feature introduces a secure integration layer to HereCRM to automate data ingestion from ad platforms (Leads, Requests) and report "Booked" conversions back to Meta/Facebook. It utilizes an Event-Driven Architecture via the existing `EventBus` to asynchronously dispatch webhooks and CAPI events without blocking user flows. Authentication is managed via database-backed API keys, provisioned through a secure signed-URL flow.

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: FastAPI, Pydantic, AIOHTTP (for outbound requests)
**Storage**: PostgreSQL (via existing ORM)
**Testing**: pytest (Unit & Integration)
**Target Platform**: Linux server
**Project Type**: Single project (Backend)
**Performance Goals**: Non-blocking dispatch (<50ms added to main request), eventually consistent delivery.
**Constraints**: Zero impact on "Book Job" transaction latency.
**Scale/Scope**: Low volume (<100 events/day), high reliability required.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **LLM-First Text Processing**: N/A - This is a deterministic API integration feature.
- **Intent Transparency**: N/A - Backend-to-backend communication. Failures logged for admin visibility.
- **Progressive Documentation**:
  - **Helpful Messages**: Error messages for API endpoints must be clear for integrators.
  - **Assistant Knowledge**: Update `src/assets/manual.md` with details on how to generate generic webhook signatures and configure Meta CAPI.

## Project Structure

### Documentation (this feature)

```
kitty-specs/015-ad-automation-integrations/
├── plan.md              # This file
├── research.md          # Skipped (Stack confirmed)
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output
```

### Source Code (repository root)

```
src/
├── models/
│   └── integration_config.py  # New model for API Keys & Webhook Config
├── api/
│   └── v1/
│       └── integrations.py    # New inbound endpoints (Leads, Requests, Provision)
├── services/
│   └── integration_service.py # Core logic for provisioning and ingest
├── handlers/                  # Event Consumers
│   └── integration_handlers.py # Meta CAPI & Webhook dispatch logic
└── events.py                  # Integration with existing global EventBus

tests/
├── integration/
│   └── test_integrations_api.py
└── unit/
    └── test_event_dispatch.py
```

**Structure Decision**: Standard backend module expansion. New `handlers/` directory introduced to organize event consumers cleanly.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| New `IntegrationConfig` Model | Dynamic API Key management | Hardcoded env vars rejected by user for security & usability |
| EventBus + Async Handlers | Performance (Non-blocking) | Synchronous hooks would slow down critical "Book Job" user path |
