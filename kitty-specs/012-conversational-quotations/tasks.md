# Tasks: Conversational Quotations (012)

**Spec**: [spec.md](./spec.md) | **Status**: Planned

## Work Packages

### WP01: Foundation & Core Service

**Goal**: Establish the data models and core service logic for managing Quotes.
**Priority**: P0 (Blocker)
**Test Criteria**: Unit tests pass for model creation and service CRUD operations.

- [x] T001: Create `Quote` and `QuoteLineItem` models in `src/models.py`
- [x] T002: Update `Business` and `Customer` models with relationships
- [x] T003: Generate and apply Alembic migration
- [x] T004: Implement `QuoteService` class with `create_quote` logic
- [x] T005: Write unit tests for Quote models and service

### WP02: PDF Generation & Delivery

**Goal**: Enable generating PDF proposals and sending them to customers via WhatsApp.
**Priority**: P0
**Test Criteria**: PDF is generated, uploaded to S3, and link is sent via WhatsApp.

- [x] T006: Create `src/templates/quote.html` Jinja2 template
- [x] T007: Update `PDFGenerator` to support quote rendering
- [x] T008: Implement `QuoteService.generate_pdf` and `send_quote` methods
- [x] T009: Add `quote_proposal` message template to `messages.yaml`
- [x] T010: Write integration tests for PDF generation and sending flow

### WP03: LLM Tool Integration

**Goal**: Allow the AI agent to create quotes from natural language requests.
**Priority**: P1
**Test Criteria**: "Send quote..." request triggers `CreateQuoteTool` and produces a valid quote.

- [x] T011: Define `CreateQuoteInput` schema in `src/uimodels.py`
- [x] T012: Implement `CreateQuoteTool` wrapper
- [x] T013: Register tool in `src/llm_client.py`
- [x] T014: Add test for tool execution with mock service

### WP04: Confirmation Workflow

**Goal**: Enable customers to confirm quotes via text or public link, creating a Job.
**Priority**: P1
**Test Criteria**: Accepting a quote creates a Job and updates Quote status.

- [x] T015: Implement `QuoteService.confirm_quote` logic (Status update + Job creation)
- [x] T016: Implement public API endpoint for web confirmation
- [x] T017: Implement text-based "Confirm" intent handler in `whatsapp_service.py`
- [x] T018: Write tests for confirmation flow (Web and Text) and Job verification
- [x] T019: Verify end-to-end "Quote -> Confirm -> Job" flow

### WP05: Request to Quote Promotion

**Goal**: Enable promoting an existing customer request to a formal Quote.
**Priority**: P2
**Test Criteria**: "Promote request" action successfully creates a Quote populated with request details.

- [x] T020: Implement `QuoteService.create_from_request` logic
- [x] T021: Add "Promote to Quote" action to `ConvertRequestTool`
- [x] T022: Update `WhatsAppService` to handle "Promote to Quote" intent/flow
- [x] T023: Write tests for Request -> Quote promotion

### WP06: Tax Calculation Integration

**Goal**: Integrate Stripe Tax API for accurate tax calculation on quotes.
**Priority**: P1
**Test Criteria**: Quotes display accurate tax calculations and preserve tax data when converting to Jobs.

- [ ] T024: Reuse `StripeTaxService` from spec 006 for quote tax calculations
- [ ] T025: Add tax fields to `Quote` model (`subtotal`, `tax_amount`, `tax_rate`, `total_amount`)
- [ ] T026: Create Alembic migration for Quote model tax fields
- [ ] T027: Update `QuoteService.create_quote` to integrate tax calculation
- [ ] T028: Update `QuoteService.confirm_quote` to preserve tax data when creating Job
- [ ] T029: Update quote HTML template to display tax breakdown
- [ ] T030: Implement tax recalculation when quote line items are modified
- [ ] T031: Add unit tests for quote tax calculation
- [ ] T032: Add integration tests for quote-to-job tax preservation
- [ ] T033: Handle tax calculation errors gracefully with fallback to 0% tax
