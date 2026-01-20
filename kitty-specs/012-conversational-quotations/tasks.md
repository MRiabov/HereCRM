# Tasks: Conversational Quotations (012)

**Spec**: [spec.md](./spec.md) | **Status**: Planned

## Work Packages

### WP01: Foundation & Core Service

**Goal**: Establish the data models and core service logic for managing Quotes.
**Priority**: P0 (Blocker)
**Test Criteria**: Unit tests pass for model creation and service CRUD operations.

- [x] T001: Create `Quote` and `QuoteLineItem` models in `src/models.py`
- [x] T002: Update `Business` and `Customer` models with relationships
- [ ] T003: Generate and apply Alembic migration
- [ ] T004: Implement `QuoteService` class with `create_quote` logic
- [ ] T005: Write unit tests for Quote models and service

### WP02: PDF Generation & Delivery

**Goal**: Enable generating PDF proposals and sending them to customers via WhatsApp.
**Priority**: P0
**Test Criteria**: PDF is generated, uploaded to S3, and link is sent via WhatsApp.

- [x] T006: Create `src/templates/quote.html` Jinja2 template
- [x] T007: Update `PDFGenerator` to support quote rendering
- [ ] T008: Implement `QuoteService.generate_pdf` and `send_quote` methods
- [ ] T009: Add `quote_proposal` message template to `messages.yaml`
- [ ] T010: Write integration tests for PDF generation and sending flow

### WP03: LLM Tool Integration

**Goal**: Allow the AI agent to create quotes from natural language requests.
**Priority**: P1
**Test Criteria**: "Send quote..." request triggers `CreateQuoteTool` and produces a valid quote.

- [ ] T011: Define `CreateQuoteInput` schema in `src/uimodels.py`
- [ ] T012: Implement `CreateQuoteTool` wrapper
- [ ] T013: Register tool in `src/llm_client.py`
- [ ] T014: Add test for tool execution with mock service

### WP04: Confirmation Workflow

**Goal**: Enable customers to confirm quotes via text or public link, creating a Job.
**Priority**: P1
**Test Criteria**: Accepting a quote creates a Job and updates Quote status.

- [ ] T015: Implement `QuoteService.confirm_quote` logic (Status update + Job creation)
- [ ] T016: Implement public API endpoint for web confirmation
- [ ] T017: Implement text-based "Confirm" intent handler in `whatsapp_service.py`
- [ ] T018: Write tests for confirmation flow (Web and Text) and Job verification
- [ ] T019: Verify end-to-end "Quote -> Confirm -> Job" flow
