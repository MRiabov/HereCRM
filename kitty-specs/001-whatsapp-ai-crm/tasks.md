# Implementation Tasks: WhatsApp AI CRM

**Feature**: WhatsApp AI CRM
**Status**: Planned
**Work Packages**: 6

## Work Package 1: Scaffolding & Core Models

**Goal**: Establish the database schema, FastAPI project structure, and secure multi-tenant data access.
**Priority**: Critical - Foundational
**Test**: `pytest tests/test_models.py` (Verify tenant isolation explicitly)

- [ ] **T001**: Setup FastAPI project structure and Async SQLite database connection (SQLAlchemy). [[WP01-scaffolding-and-models.md]]
- [ ] **T002**: Implement `Business` and `User` SQLAlchemy models and Pydantic schemas. [[WP01-scaffolding-and-models.md]]
- [ ] **T003**: Implement `Customer`, `Job`, `Request` models and schemas. [[WP01-scaffolding-and-models.md]]
- [ ] **T004**: Implement `ConversationState` model for state management. [[WP01-scaffolding-and-models.md]]
- [ ] **T005**: Implement CRUD Repository layer with mandatory Tenant Isolation (Business ID check). [[WP01-scaffolding-and-models.md]]

---

## Work Package 2: LLM Parsing Engine

**Goal**: Create the intelligence layer that converts natural language into structured tool calls.
**Priority**: High - Core Feature
**Test**: `pytest tests/test_llm_parser.py` (Verify extraction accuracy >95% on sample set)

- [x] **T006**: Setup Gemini Client wrapper and configuration. [[WP02-llm-parsing-engine.md]]
- [x] **T007**: Define Pydantic models for Tools (`AddJob`, `ScheduleJob`, `StoreRequest`, `ConvertRequest`). [[WP02-llm-parsing-engine.md]]
- [x] **T008**: Implement `LLMParser.parse(text)` with refined classification logic (Price/Desc -> Job, "add request" -> Request, Time -> Schedule). [[WP02-llm-parsing-engine.md]]
- [x] **T009**: Write unit tests for `LLMParser` covering user-specified intent nuances. [[WP02-llm-parsing-engine.md]]

---

## Work Package 3: Core CRM Logic & State Machine

**Goal**: Implement the business logic for handling commands, confirmations, drafts, and undo operations.
**Priority**: High - Core Feature
**Test**: `pytest tests/test_state_machine.py` (Verify state transitions IDLE -> CONFIRM -> IDLE)

- [x] **T010**: Implement `WhatsappService` class structure. [[WP03-core-crm-logic-and-state.md]]
- [x] **T011**: Implement Confirmation Flow: Save draft to `ConversationState`, handle "Yes/No". [[WP03-core-crm-logic-and-state.md]]
- [x] **T012**: Implement Undo Logic: Transaction rollback or compensation mechanism. [[WP03-core-crm-logic-and-state.md]]
- [ ] **T012b**: Implement "Edit Last" Logic: Generate edit prompt from last action metadata. [[WP03-core-crm-logic-and-state.md]]
- [x] **T012a**: Implement Request Conversion Logic (Promote Request -> Job). [[WP03-core-crm-logic-and-state.md]]
- [x] **T013**: Wire up Tool Execution: Map LLM Tool Calls to Repository CRUD methods. [[WP03-core-crm-logic-and-state.md]]

---

## Work Package 4: Onboarding & End-to-End Wiring

**Goal**: Connect the Webhook to the logic layer and implement the zero-friction onboarding.
**Priority**: Medium - Integration
**Test**: `pytest tests/test_webhook.py` (Mocked end-to-end flow)

- [x] **T014**: Implement FastAPI Webhook Entrypoint (`POST /webhook`). [[WP04-onboarding-and-integration.md]]
- [x] **T015**: Implement Middleware/Service logic for User Identification (auto-create Business/User if new). [[WP04-onboarding-and-integration.md]]
- [x] **T016**: Connect Webhook -> Service -> LLM -> DB pipeline. [[WP04-onboarding-and-integration.md]]
- [x] **T017**: Write Integration Tests for Scenario 1 (Add: Job). [[WP04-onboarding-and-integration.md]]

---

## Work Package 5: Refinement & Productionizing

**Goal**: Handle edge cases, ambiguous inputs, scheduling specifics, and final polish.
**Priority**: Low - Polish
**Test**: Manual E2E Walkthrough

- [ ] **T018**: Implement specific logic for "Schedule" command (updating existing records). [[WP05-refinement-and-productionizing.md]]
- [ ] **T019**: Refine error handling: Display helpful error + Help message for unparseable inputs instead of storing as Request. [[WP05-refinement-and-productionizing.md]]
- [ ] **T019a**: Implement "Help" command to explain bot usage. [[WP05-refinement-and-productionizing.md]]
- [ ] **T020a**: Implement Configurable YAML Boilerplates for customer messages. [[WP05-refinement-and-productionizing.md]]
- [ ] **T020b**: Refactor hardcoded messages to use YAML templates. [[WP05-refinement-and-productionizing.md]]
- [ ] **T020c**: Verify refined intent nuances with `chat_simulator.py`. [[WP05-refinement-and-productionizing.md]]
- [ ] **T020**: Perform final E2E Walkthrough and verify all Success Criteria. [[WP05-refinement-and-productionizing.md]]

---

## Work Package 6: Security Hardening

**Goal**: Protect the application against common web vulnerabilities and Ensure multi-tenant safety.
**Priority**: High - Security
**Test**: `pytest tests/test_security.py` (Verify rate limiting, input validation, and tenant isolation)

- [x] **T021**: Implement Rate Limiting middleware for the webhook endpoint. [[WP06-security-hardening.md]]
- [x] **T022**: Implement Input Validation and character limits for Webhook payload and LLM Tool arguments. [[WP06-security-hardening.md]]
- [x] **T023**: Harden LLM System Instructions to prevent prompt injection and restrict `UpdateSettingsTool` keys. [[WP06-security-hardening.md]]
- [x] **T024**: Implement a security audit tool/script to verify multi-tenant scoping in the repository layer. [[WP06-security-hardening.md]]
- [x] **T025**: Refactor error handling to return generic messages and prevent PII leakage in logs. [[WP06-security-hardening.md]]
