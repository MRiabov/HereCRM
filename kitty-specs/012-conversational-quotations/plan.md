# Implementation Plan: 012-conversational-quotations

**Branch**: `012-conversational-quotations` | **Date**: 2026-01-20 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/kitty-specs/012-conversational-quotations/spec.md`

**Note**: This template is filled in by the `/spec-kitty.plan` command. See `.kittify/templates/commands/plan.md` for the execution workflow.

The planner will not begin until all planning questions have been answered—capture those answers in this document before progressing to later phases.

## Summary

Implement a conversational quotation system that allows business owners to generate price proposals using natural language (e.g., "send a quote to John for window cleaning"). Quotes are stored as persistent entities with a lifecycle (DRAFT, SENT, ACCEPTED). Acceptance is triggered via a text reply "Confirm" (resolving to the most recent quote) or through a secure link on an external website (`HereCRMWebsite`). PDF generation, S3 storage, and intent detection patterns will be adapted from Spec 006.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: `weasyprint`, `jinja2`, `boto3`, `sqlmodel`
**Storage**: PostgreSQL, S3 (Backblaze B2) for PDFs
**Testing**: `pytest`
**Target Platform**: Linux server
**Project Type**: Single project
**Performance Goals**: Quote generation and transmission < 3 seconds
**Constraints**: Secure token-based confirmation for external website
**Scale/Scope**: 100% automation of "Confirm" replies to Job creation

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- LLM-First Text Processing: [PASS] Quote creation and confirmation intent will use LLM tools.
- Intent Transparency and Control: [PASS] System with notify users of quote creation and allow cancellation/editing via text or CRM.
- No Brittle Parsing: [PASS] Use Pydantic models for LLM output validation.

## Project Structure

### Documentation (this feature)

```
kitty-specs/[###-feature]/
├── plan.md              # This file (/spec-kitty.plan command output)
├── research.md          # Phase 0 output (/spec-kitty.plan command)
├── data-model.md        # Phase 1 output (/spec-kitty.plan command)
├── quickstart.md        # Phase 1 output (/spec-kitty.plan command)
├── contracts/           # Phase 1 output (/spec-kitty.plan command)
└── tasks.md             # Phase 2 output (/spec-kitty.tasks command - NOT created by /spec-kitty.plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```bash
src/
├── models.py            # Quote, QuoteLineItem models
├── services/
│   ├── quote_service.py # Core logic for quotes
│   ├── pdf_generator.py # Refactored common logic + Quote spec
│   └── storage.py       # Reused S3 service
├── tools/
│   └── quote_tools.py   # LLM tools for creating quotes
└── api/
    └── public.py        # Confirmation endpoint
```

**Structure Decision**: Option 1: Single project.

## Complexity Tracking

[Fill ONLY if Constitution Check has violations that must be justified]

| Violation | Why Needed | Simpler Alternative Rejected Because |
| :--- | :--- | :--- |
| N/A | | |
