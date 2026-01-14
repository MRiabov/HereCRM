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

- `Business`: Tenant root. **New**: `settings` (JSON) for defaults like `default_city`, `default_country`.
- `User`: Linked to Business (many-to-one). Phone number is unique. **New**: `timezone` field (default 'UTC').
- `Customer`: Linked to Business. Is defined as Lead if no Job is attached. **New**: `street`, `city`, `country`, `original_address_input`, `created_at` timestamp, `latitude`, `longitude`.
- `Job`: Linked to Business & Customer. **New**: `created_at` timestamp, `latitude`, `longitude`.
- `Request`: Unstructured requests. **New**: `created_at` timestamp.
- `ConversationState`: For multi-turn flows (confirmations, ambiguities).
  - Fields: `phone_number`, `state_enum` (IDLE, WAITING_CONFIRM), `draft_data` (JSON), `last_updated`, `last_action_metadata`.

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
- Defines tools:
  - `AddJobTool`: identifying a job request (has price or job task description).
  - `AddCustomerTool`: identifying a lead/client/customer (no job details). We first search for a customer! Extracts `street`, `city`, `country`, `original_address_input`. Defaults for city/country applied from Business settings if missing.
  - `EditCustomerTool`: updating customer details.
  - `EditCustomerTool`: updating customer details.
  - `StoreRequestTool`: storing generic requests.
  - `SearchTool`: **Enhanced** to support structured queries:
    - `entity_type` (Job, Customer, Request, Lead).
    - `query_type` (General, Added, Scheduled).
    - `min_date` / `max_date` (ISO strings for flexible date ranges).
    - `status` (pending, done, etc.).
- Classification Logic:
  - If a price tag or job description is supplied -> `AddJob`.
  - If "add:" is explicitly followed by "request" -> `StoreRequest`.
  - If "add lead" or just a person's details without job info -> `AddCustomerTool`.
  - **Definition**: A "Lead" is explicitly defined as a **Customer with no associated Jobs**.
- Returns structured Tool Calls.

#### [NEW] [tools.py](file:///home/maksym/Work/proj/HereCRM/.worktrees/001-whatsapp-ai-crm/src/tools.py)

- Implementation of tool logic (CRUD operations).
- **Security Check**: Enforce Tenant Isolation (Business ID) on every query.

- **Security Check**: Enforce Tenant Isolation (Business ID) on every query.

#### [NEW] [template_service.py](file:///home/maksym/Work/proj/HereCRM/.worktrees/001-whatsapp-ai-crm/src/services/template_service.py)

- `TemplateService` class to load and render messages from YAML.
- **Source**: `src/assets/messages.yaml`.
- **Method**: `get_message(key, **kwargs)` with variable interpolation.

### UX Flows

1. **Mutation**: User says "Add job..." -> LLM parses -> App saves draft to `ConversationState` -> App replies "Confirm? [Yes/No]"
2. **Confirmation**: User says "Yes" -> App reads draft -> commits to DB -> Clears State -> Replies "Saved. [Undo | Edit]".
3. **Undo**: User says "Undo" -> App checks `last_action_metadata` -> Reverses DB change.
4. **Edit Last**: User says "edit last" -> App checks `last_action_metadata` -> Generates prompt from metadata -> Replies with edit instructions.
5. **Error Handling**: If LLM cannot parse input -> App replies "Sorry, we couldn't understand your request" + Help block.

## Verification Plan

### Automated Tests

- **Unit Tests**:
  - `test_models.py`: Verify isolation (User A cannot see User B's jobs).
  - `test_llm_parser.py`: Feed sample texts ("Add John...") and assert correct Tool Call output.
  - `test_state_machine.py`: Simulate multi-turn flows (Command -> Wait -> Confirm).
- **Integration Tests**:
  - `test_webhook.py`: Mock WhatsApp request -> Verify DB state changes.
  - `test_search_features.py`: **New** Test suite covering 15+ complex search scenarios:
    - "jobs scheduled for today" vs "jobs added today"
    - "customers with jobs today"
    - "leads added yesterday" (filtering customers w/o jobs + date)
    - "leads added yesterday" (filtering customers w/o jobs + date)
    - "search within 200m of..." (Geo-spatial proximity)
    - Timezone-aware date calculations.

### Geo-Spatial Verification

- Verify `haversine_distance` calculation in Repositories.
- Verify mocks for Geocoding (London/Dublin).
- Ensure coordinates are correctly stored on create/add.

### Manual Verification

- **E2E Walkthrough**:
    1. Send "Hello" from Phone A -> Verify Business A created.
    2. Send "Add Job..." -> Verify Confirmation Prompt.
    3. Type "Yes" -> Verify Job in DB.
    4. Type "Undo" -> Verify Job removed.
    5. Send "Add User Phone B" -> Verify Phone B added to Business A.
    6. Send message from Phone B -> Verify access to Business A data.
