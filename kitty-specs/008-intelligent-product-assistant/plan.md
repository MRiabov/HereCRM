# Implementation Plan: Intelligent Product Assistant

*Path: kitty-specs/008-intelligent-product-assistant/plan.md*

**Branch**: `008-intelligent-product-assistant` | **Date**: 2026-01-19 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/008-intelligent-product-assistant/spec.md`

**Note**: This template is filled in by the `/spec-kitty.plan` command. See `.kittify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement an intelligent RAG-based assistant that leverages the product manual and conversation history to provide "How-to" guidance and troubleshooting for users. The system will use **Prompt Injection** to provide the manual as context to a sub-agent LLM call, triggered by the existing `HelpTool`.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: FastAPI, SQLAlchemy, OpenAI/OpenRouter (LLM), Pydantic  
**Storage**: PostgreSQL (via existing Message model)  
**Testing**: pytest  
**Target Platform**: Linux/Cloud
**Project Type**: single
**Performance Goals**: Help responses delivered < 2s (SC-003)
**Constraints**: Concise responses for SMS/WhatsApp, detailed for Email
**Scale/Scope**: Support last 5 messages of context

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Directive | Status | Notes |
|-----------|--------|-------|
| 1. LLM-First | PASS | Uses LLM semantic understanding for help queries. |
| 2. User Confirmation | PASS | Static guidance is read-only; write operations initiated via help (if any) will trigger standard confirmation. |

## Project Structure

### Documentation (this feature)

```
kitty-specs/008-intelligent-product-assistant/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output
```

### Source Code (repository root)

```
src/
├── models.py            # Existing models (Message, User)
├── config.py            # Configuration loading (new ChannelConfig)
├── llm_client.py        # LLM interaction logic (new chat_completion)
├── tool_executor.py     # Tool execution (HelpTool)
├── services/
│   ├── help_service.py  # [NEW] RAG orchestration
│   └── whatsapp_service.py # Integration point
└── assets/
    ├── prompts.yaml     # Prompt templates
    ├── manual.md        # Product manual
    └── channels.yaml    # [NEW] Channel-specific settings
```

**Structure Decision**: Single Project (Standard). The logic is encapsulated in a new `HelpService` to maintain SRP.

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | | |
