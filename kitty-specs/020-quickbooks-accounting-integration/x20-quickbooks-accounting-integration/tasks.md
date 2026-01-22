# Tasks: QuickBooks Accounting Integration

**Spec**: [spec.md](spec.md) | **Status**: In Progress

## Work Packages

### WP01: Foundation & Data Model

- **Goal**: Set up database schemas for credentials (encrypted) and sync metadata (main DB).
- **Priority**: High (Blocking)
- **Status**: Todo
- **Subtasks**:
  - [ ] T001: Add sync status fields to Business, Customer, Service, Invoice, Payment models
  - [ ] T002: Create SyncLog model and QuickBooksCredential model (for encrypted DB)
  - [ ] T003: Create Alembic migration script for all schema changes
  - [ ] T004: Configure `credentials_db` engine and session factory in `database.py`
  - [ ] T005: Add tests for database models and encrypted DB access logic

### WP02: OAuth Infrastructure

- **Goal**: Implement secure OAuth 2.0 authentication flow and token management.
- **Dependencies**: WP01
- **Status**: Todo
- **Subtasks**:
  - [ ] T006: Create `QuickBooksClient` wrapper using `python-quickbooks` SDK
  - [ ] T007: Implement `QuickBooksAuth` service (Auth URL generation, callback handling)
  - [ ] T008: Implement secure token storage and retrieval logic using `QuickBooksCredential`
  - [ ] T009: Implement proactive token refresh logic
  - [ ] T010: Add integration tests for OAuth flow (mocking external API)

### WP03: Sync Logic - Base & Dependencies

- **Goal**: Implement base sync architecture and synchronization for independent entities (Customers, Services).
- **Dependencies**: WP02
- **Status**: Todo
- **Subtasks**:
  - [ ] T011: Define `QuickBooksSyncer` base class and mapper interfaces
  - [ ] T012: Implement `CustomerSyncer` and data mapper (HereCRM -> QB Customer)
  - [ ] T013: Implement `ServiceSyncer` and data mapper (HereCRM Service -> QB Item)
  - [ ] T014: Add unit tests for Customer and Service mapping/sync logic

### WP04: Sync Logic - Invoices & Payments

- **Goal**: Implement synchronization for transaction entities (Invoices, Payments).
- **Dependencies**: WP03
- **Status**: Todo
- **Subtasks**:
  - [ ] T015: Implement `InvoiceSyncer` and mapper (Including line items & tax references)
  - [ ] T016: Implement `PaymentSyncer` and mapper (Linking to Invoices)
  - [ ] T017: Implement linked transaction logic (Ensure parent Customer/Invoice exists before sync)
  - [ ] T018: Add unit tests for Invoice and Payment sync logic

### WP05: Orchestration & Scheduler

- **Goal**: Implement the hourly batch job and global sync orchestration.
- **Dependencies**: WP04
- **Status**: Todo
- **Subtasks**:
  - [ ] T019: Implement `QuickBooksSyncManager` to orchestrate entity sync order
  - [ ] T020: Implement batch processing, error handling, and `SyncLog` recording
  - [ ] T021: Configure APScheduler job for hourly sync execution
  - [ ] T022: Implement manual sync trigger logic
  - [ ] T023: Add integration tests for full sync cycle

### WP06: User Interface (Accounting State)

- **Goal**: Implement the conversational interface for managing QuickBooks integration.
- **Dependencies**: WP05
- **Status**: Todo
- **Subtasks**:
  - [ ] T024: Create `ACCOUNTING` conversation state in `whatsapp_service.py`
  - [ ] T025: Create tools: `ConnectQB`, `DisconnectQB`, `SyncQB`, `QBStatus`
  - [ ] T026: Implement "Connect" flow (Send Auth Link -> Wait for Callback -> Notify)
  - [ ] T027: Implement status reporting tool (Format `SyncLog` data for users)
  - [ ] T028: Add tests for `ACCOUNTING` state transitions and tool usage

### WP07: Documentation & Final Polish

- **Goal**: Finalize user documentation and ensure system readiness.
- **Dependencies**: WP06
- **Status**: Todo
- **Subtasks**:
  - [ ] T029: Update `src/assets/manual.md` with QuickBooks integration guides
  - [ ] T030: Update `src/assets/messages.yaml` with all new response templates
  - [ ] T031: Perform final end-to-end verification and checklist run
