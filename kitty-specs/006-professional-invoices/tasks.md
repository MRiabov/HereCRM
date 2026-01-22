# Implementation Tasks - Feature 006

## Status Board

| ID | Work Package | Status | Owner |
|---|---|---|---|
| WP01 | Infrastructure & Data Model | [x] | antigravity |
| WP02 | Invoice PDF Generation | [x] | Antigravity |
| WP03 | Logic, Tools & Integration | [x] | gemini-cli |
| WP04 | Tax Calculation Integration | [ ] | |
| WP05 | Payment Link Integration | [x] | antigravity |

## Work Packages

### WP01: Infrastructure & Data Model

**Goal**: Set up S3 storage, database models, and dependencies.
**Priority**: P0 (Foundational)
**Prompt**: [tasks/WP01-infrastructure-and-models.md](tasks/WP01-infrastructure-and-models.md)

- [x] T001: Install Python dependencies (`boto3`, `weasyprint`, `jinja2`).
- [x] T002: Update `.env` and `config` to support S3.
- [x] T003: Implement `S3Service` in `src/services/storage.py` with mockable interface.
- [x] T004: Create `Invoice` model in `src/database/models.py`.
- [x] T005: Update `Job` model relationship.
- [x] T006: Create and run Alembic migration.

### WP02: Invoice PDF Generation

**Goal**: Create the mechanism to turn data into professional PDFs.
**Priority**: P1
**Prompt**: [tasks/WP02-invoice-generation.md](tasks/WP02-invoice-generation.md)

- [x] T007: Create professional HTML template `src/templates/invoice.html` (Jinja2).
- [x] T008: Implement `InvoicePDFGenerator` in `src/services/pdf_generator.py`.
- [x] T009: Add unit tests for PDF generation (mocking data, checking output bytes).

### WP03: Logic, Tools & Integration

**Goal**: Connect the "Send Invoice" command to the generation and delivery pipeline.
**Priority**: P1
**Prompt**: [tasks/WP03-invoice-logic-and-tools.md](tasks/WP03-invoice-logic-and-tools.md)

- [x] T010: Implement `InvoiceService` (orchestrates `PDFGenerator` + `S3Service` + DB).
- [x] T011: Implement `SendInvoiceTool` (Customer Lookup -> Last Job -> InvoiceService).
- [x] T012: Register `SendInvoiceTool` in `LLMClient`.
- [x] T013: Update `WhatsAppService` to handle `SendInvoiceTool` output (send file/link).
- [x] T014: Add integration tests for the full flow (mocking S3).

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

### WP05: Payment Link Integration

**Goal**: Allow businesses to add a payment link that appears on the PDF and in messages.
**Priority**: P1
**Prompt**: [tasks/WP05-payment-link-integration.md](tasks/WP05-payment-link-integration.md)

- [x] T026: Add `payment_link` field to `Business` model.
- [x] T027: Add `payment_link` (snapshot) field to `Invoice` model.
- [x] T028: Create Alembic migration for payment link fields.
- [x] T029: Update `src/templates/invoice.html` to include a "Pay Now" button if payment link is present.
- [x] T030: Update `InvoiceService` to include the business's payment link when generating and saving an invoice.
- [x] T031: Update `SendInvoiceTool` and `WhatsAppService` to include the payment link in the outgoing message.
- [x] T032: Add unit and integration tests for payment link presence in PDF and messages.
