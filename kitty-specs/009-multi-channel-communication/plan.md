# Implementation Plan: Multi-channel Communication

*Path: kitty-specs/009-multi-channel-communication/plan.md*

**Branch**: `009-multi-channel-communication` | **Date**: 2026-01-19 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/009-multi-channel-communication/spec.md`

**Note**: This template is filled in by the `/spec-kitty.plan` command. See `.kittify/templates/commands/plan.md` for the execution workflow.

The planner will not begin until all planning questions have been answered—capture those answers in this document before progressing to later phases.

## Summary

Implement multi-channel communication support including TextGrid (default SMS), Twilio (optional SMS), Postmark (Email), and a detailed Generic Webhook. Refactor SMS logic behind an `SMSMessagingService` interface to support switching providers. Refactor the `User` model to support multiple identities (email/phone) with an Integer ID. Introduce a configurable "Auto-Confirmation" state machine.

## Technical Context

**Language/Version**: Python 3.12 (inferred from environment)
**Primary Dependencies**: TextGrid SDK (or API), Twilio SDK, Postmark SDK (or requests), FastAPI/Streamlit (existing stack), SqlAlchemy/Alembic (DB).
**Storage**: PostgreSQL (existing)
**Testing**: pytest
**Target Platform**: Linux server / Containerized
**Project Type**: Web Application + Background Services
**Performance Goals**: <2s processing latency for SMS/Email
**Constraints**: Cost optimization for SMS (concise messages), auto-confirmation reliability.
**Scale/Scope**: Core model refactor, 3 new integrations, state machine update.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### 1. LLM-First Text Processing

* **Compliance**: Yes. Inbound messages from new channels will flow through the same LLM processing pipeline as WhatsApp.

### 2. Mandatory User Confirmation

* **Conflict**: The feature explicitly requests **Auto-Confirmation** for SMS/Email after a timeout.
* **Justification**: This is a cost and UX optimization for high-latency/expensive channels requested by the user. The "risk" is mitigated by the 45s cancellation window. This is a deliberate exception to the "Explicit Confirmation" rule for these specific channels.

## Project Structure

### Documentation (this feature)

```text
kitty-specs/009-multi-channel-communication/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output
```

### Source Code (repository root)

```text
src/
├── models/              # User, ChannelConfig updates
├── services/
│   ├── channels/        # Twilio, Postmark, Webhook implementations
│   └── confirmation/    # Auto-confirmation logic
├── api/
│   └── webhooks/        # Inbound webhook endpoints
└── lib/

tests/
├── integration/         # Channel integration tests
└── unit/                # State machine tests
```

**Structure Decision**: Extending existing Single Project structure.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Auto-Confirmation (Constitution) | Cost/UX optimization for SMS/Email | Manual confirmation is too slow/expensive for these channels. |
