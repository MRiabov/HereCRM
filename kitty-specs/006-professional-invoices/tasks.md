# Implementation Tasks - Feature 006

## Status Board

| ID | Work Package | Status | Owner |
|---|---|---|---|
| WP01 | Infrastructure & Data Model | [x] | antigravity |
| WP02 | Invoice PDF Generation | [ ] | |
| WP03 | Logic, Tools & Integration | [ ] | |

## Work Packages

### WP01: Infrastructure & Data Model

**Goal**: Set up S3 storage, database models, and dependencies.
**Priority**: P0 (Foundational)
**Prompt**: [tasks/WP01-infrastructure-and-models.md](tasks/WP01-infrastructure-and-models.md)

- [ ] T001: Install Python dependencies (`boto3`, `weasyprint`, `jinja2`).
- [ ] T002: Update `.env` and `config` to support S3.
- [ ] T003: Implement `S3Service` in `src/services/storage.py` with mockable interface.
- [ ] T004: Create `Invoice` model in `src/database/models.py`.
- [ ] T005: Update `Job` model relationship.
- [ ] T006: Create and run Alembic migration.

### WP02: Invoice PDF Generation

**Goal**: Create the mechanism to turn data into professional PDFs.
**Priority**: P1
**Prompt**: [tasks/WP02-invoice-generation.md](tasks/WP02-invoice-generation.md)

- [ ] T007: Create professional HTML template `src/templates/invoice.html` (Jinja2).
- [ ] T008: Implement `InvoicePDFGenerator` in `src/services/pdf_generator.py`.
- [ ] T009: Add unit tests for PDF generation (mocking data, checking output bytes).

### WP03: Logic, Tools & Integration

**Goal**: Connect the "Send Invoice" command to the generation and delivery pipeline.
**Priority**: P1
**Prompt**: [tasks/WP03-invoice-logic-and-tools.md](tasks/WP03-invoice-logic-and-tools.md)

- [ ] T010: Implement `InvoiceService` (orchestrates `PDFGenerator` + `S3Service` + DB).
- [ ] T011: Implement `SendInvoiceTool` (Customer Lookup -> Last Job -> InvoiceService).
- [ ] T012: Register `SendInvoiceTool` in `LLMClient`.
- [ ] T013: Update `WhatsAppService` to handle `SendInvoiceTool` output (send file/link).
- [ ] T014: Add integration tests for the full flow (mocking S3).
