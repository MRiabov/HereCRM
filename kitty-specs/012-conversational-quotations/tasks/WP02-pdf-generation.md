---
work_package_id: WP02
title: PDF Generation & Delivery
lane: "doing"
dependencies: []
subtasks: [T006, T007, T008, T009, T010]
reviewed_by: "MRiabov"
review_status: "approved"
agent: "Antigravity"
shell_pid: "3779362"
---

### Objective

Implement the generation of professional PDF proposals and the mechanism to deliver them to customers via WhatsApp/SMS.

### Context

Similar to Invoices, Quotes need to be rendered as PDFs, uploaded to S3, and a public link sent to the customer. We will reuse `PDFGenerator` and `StorageService`.

### Subtasks

#### T006: Create Quote Template

**Purpose**: HTML layout for the quote PDF.
**Steps**:

1. Create `src/templates/quote.html`.
2. Use Jinja2 syntax. Include:
   - Business Logo/Details.
   - Customer Details.
   - "QUOTE" header.
   - Line Items table (Description, Qty, Unit Price, Total).
   - Grand Total.
   - "Accept" button/link pointing to `{{ confirm_url }}`.

#### T007: Update PDFGenerator

**Purpose**: Logic to render the template.
**Steps**:

1. Edit `src/services/pdf_generator.py`.
2. Add `generate_quote_pdf(quote: Quote, business: Business, customer: Customer) -> bytes`.
3. Use `weasyprint` to render `src/templates/quote.html`.

#### T008: Implement Send Logic

**Purpose**: Coordinate generation, upload, and messaging.
**Steps**:

1. Edit `src/services/quote_service.py`.
2. Add dependency on `PDFGenerator`, `StorageService`, `WhatsappService` (or `MessagingService`).
3. Implement `send_quote(quote_id, channel="whatsapp")`:
   - Fetch Quote, Business, Customer.
   - Generate PDF bytes.
   - Upload to S3 (bucket: `quotes`, key: `quote_{id}.pdf`).
   - Update `quote.blob_url` and set status to `SENT`.
   - Construct message with link.
   - Send via `MessagingService`.

#### T009: Message Templates

**Purpose**: Define the text sent to the customer.
**Steps**:

1. Edit `src/assets/messages.yaml`.
2. Add `quote_proposal`:
   - Text: "Hi {{ name }}, here is your quote for {{ total }}: {{ link }}. Reply 'Confirm' to book."

#### T010: Integration Tests

**Purpose**: Verify the send pipeline.
**Steps**:

1. Edit/Create `tests/integration/test_quote_flow.py`.
2. Mock `StorageService.upload` and `MessagingService.send`.
3. Call `quote_service.send_quote()`.
4. Assert PDF generated, Upload called, Message sent, Status updated.

### Verification

- Run `pytest tests/integration/test_quote_flow.py`.

## Activity Log

- 2026-01-20T18:14:35Z – unknown – lane=done – Review passed: Implemented fuzzy name search and enhanced assignment logic with conflict detection. Added comprehensive unit tests.
- 2026-01-20T18:34:34Z – Antigravity – shell_pid=3779362 – lane=doing – Started implementation via workflow command
- 2026-01-20T18:50:40Z – Antigravity – shell_pid=3779362 – lane=for_review – Implemented T006-T010: Quote PDF generation template, S3 upload integration in QuoteService, and message delivery via MessagingService. Added integration tests.
- 2026-01-20T19:09:20Z – Antigravity – shell_pid=3779362 – lane=doing – Started review via workflow command
