# Implementation Tasks - Feature 006

## Status Board

| ID | Work Package | Status | Owner |
|---|---|---|---|
| WP01 | Infrastructure & Data Model | [x] | antigravity |
| WP02 | Invoice PDF Generation | [ ] | |
| WP03 | Logic, Tools & Integration | [ ] | |
| WP04 | Tax Calculation Integration | [ ] | |

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

### WP04: Tax Calculation Integration

**Goal**: Integrate Stripe Tax API for accurate tax calculation on invoices.
**Priority**: P1
**Prompt**: [tasks/WP04-tax-calculation.md](tasks/WP04-tax-calculation.md)

- [ ] T015: Install `stripe` Python SDK and add to dependencies.
- [ ] T016: Add Stripe configuration to `.env` (`STRIPE_SECRET_KEY`, `STRIPE_TAX_ENABLED`).
- [ ] T017: Implement `StripeTaxService` in `src/services/tax_service.py` with tax calculation methods.
- [ ] T018: Add `tax_mode` field to `Business` model (Enum: `tax_included`, `tax_added`).
- [ ] T019: Add tax fields to `Invoice` model (`subtotal`, `tax_amount`, `tax_rate`, `total_amount`).
- [ ] T020: Create Alembic migration for Business and Invoice model changes.
- [ ] T021: Update `InvoiceService` to integrate tax calculation before PDF generation.
- [ ] T022: Update invoice HTML template to display tax breakdown.
- [ ] T023: Add unit tests for `StripeTaxService` (mocking Stripe API).
- [ ] T024: Add integration tests for invoice generation with tax calculation.
- [ ] T025: Implement tax calculation caching to reduce API calls.
