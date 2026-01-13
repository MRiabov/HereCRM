# Implementation Plan: WhatsApp AI CRM

**Feature**: WhatsApp AI CRM
**Status**: Draft
**Mission**: software-dev

## Goal Description

Build a multi-tenant, text-driven CRM within WhatsApp. Users can manage jobs, customers, and schedules using natural language. The system parses intentions via LLM ("Add Job", "Schedule") and executes them after robust confirmation flows.

## User Review Required

> [!IMPORTANT]
> **State Management**: Pending confirmations (conflicting names, "undo" windows) will be stored in a new SQLite `conversation_state` table to survive restarts.

## Proposed Changes

### Tech Stack

- **Framework**: FastAPI (Async)
- **Database**: SQLite with SQLAlchemy (Async)
- **LLM**: Gemini (via Vertex AI or similar standard client)
- **Validation**: Pydantic

### Data Model (`models.py`)

#### [NEW] [models.py](file:///home/maksym/Work/proj/HereCRM/.worktrees/001-whatsapp-ai-crm/src/models.py)

New SQLAlchemy models for multi-tenancy:

- `Business`: Tenant root.
- `User`: Linked to Business (many-to-one). Phone number is unique.
- `Customer`: Linked to Business.
- `Job`: Linked to Business & Customer.
- `RecallRequest`: Unstructured requests.
- `ConversationState`: For multi-turn flows (confirmations, ambiguities).
  - Fields: `phone_number`, `state_enum` (IDLE, WAITING_CONFIRM), `draft_data` (JSON), `last_updated`.

### Application Logic

#### [MODIFY] [main.py](file:///home/maksym/Work/proj/HereCRM/.worktrees/001-whatsapp-ai-crm/src/main.py)

- **Refactor**: Split monolithic `webhook` into `WhatsappService`.
- **Flow**:
  1. Receive Webhook.
  2. Identify/Create User & Business (Onboarding).
  3. Retrieve Conversation State.
  4. If `WAITING_CONFIRM`: Route to `ConfirmationHandler`.
  5. If `IDLE`: Route to `LLMParser`.
  6. Execute Tool -> Update State -> Send Reply.

#### [NEW] [llm_client.py](file:///home/maksym/Work/proj/HereCRM/.worktrees/001-whatsapp-ai-crm/src/llm_client.py)

- `LLMParser` class.
- Defines tools: `add_job`, `add_customer`, `schedule_job`, `edit_customer`.
- Returns structured Tool Calls.

#### [NEW] [tools.py](file:///home/maksym/Work/proj/HereCRM/.worktrees/001-whatsapp-ai-crm/src/tools.py)

- Implementation of tool logic (CRUD operations).
- **Security Check**: Enforce Tenant Isolation (Business ID) on every query.

### UX Flows

1. **Mutation**: User says "Add job..." -> LLM parses -> App saves draft to `ConversationState` -> App replies "Confirm? [Yes/No]"
2. **Confirmation**: User says "Yes" -> App reads draft -> commits to DB -> Clears State -> Replies "Saved. [Undo]".
3. **Undo**: User says "Undo" -> App checks `last_operation_id` -> Reverses DB change.

## Verification Plan

### Automated Tests

- **Unit Tests**:
  - `test_models.py`: Verify isolation (User A cannot see User B's jobs).
  - `test_llm_parser.py`: Feed sample texts ("Add John...") and assert correct Tool Call output.
  - `test_state_machine.py`: Simulate multi-turn flows (Command -> Wait -> Confirm).
- **Integration Tests**:
  - `test_webhook.py`: Mock WhatsApp request -> Verify DB state changes.

### Manual Verification

- **E2E Walkthrough**:
    1. Send "Hello" from Phone A -> Verify Business A created.
    2. Send "Add Job..." -> Verify Confirmation Prompt.
    3. Type "Yes" -> Verify Job in DB.
    4. Type "Undo" -> Verify Job removed.
    5. Send "Add User Phone B" -> Verify Phone B added to Business A.
    6. Send message from Phone B -> Verify access to Business A data.
