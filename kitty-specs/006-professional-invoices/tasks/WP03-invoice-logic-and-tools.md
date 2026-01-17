---
type: work-package
id: WP03
lane: "for_review"
subtasks:
  - T010
  - T011
  - T012
  - T013
  - T014
agent: "antigravity"
---

# Work Package 03: Logic, Tools & Integration

## Goal

Integrate the PDF generation and S3 storage into the main application flow via a new Tool and WhatsApp service integration.

## Context

This is the final assembly. We need a service layer to coordinate checks (duplicates), generation, and storage. Then we expose this via an LLM Tool and handle the tool's output to send the file back to the user on WhatsApp.

## Subtasks

### T010: Implement `InvoiceService`

- Create `src/services/invoice_service.py`.
- Class `InvoiceService` (dependency injection: session, s3_service, pdf_generator):
  - `get_existing_invoice(job_id) -> Optional[Invoice]`
  - `create_invoice(job_id, force_regenerate=False) -> Invoice`:
    - Check if valid job.
    - If `get_existing_invoice(job_id)` is not None AND not `force_regenerate`:
      - Return existing invoice.
    - Generate PDF, Upload, Save to DB.
    - Return new invoice.

### T011: Implement `SendInvoiceTool`

- Create `src/tools/invoice_tools.py`.
- `SendInvoiceTool` (BaseTool):
  - Arguments:
    - `query`: str (customer name/phone)
    - `force_regenerate`: bool (default False)
  - Logic:
    - Find Customer (reuse search logic).
    - Find last COMPLETED Job for customer.
    - Check if Invoice exists for Job.
      - If exists and `force_regenerate=False`: Return "Invoice already exists generated on {date}. User must confirm to regenerate. Ask user if they want to 'resend existing' or 'regenerate'."
      - **Wait**: If they want to "resend existing", we just need to return the URL of existing.
      - *Refined Logic*:
        - Invoice = `service.get_existing_invoice(job.id)`
        - If Invoice exists and not `force_regenerate`:
          - Return "Invoice already exists: {url}. (Created {date})."
        - Else:
          - Invoice = `service.create_invoice(job.id, force_regenerate=True)`
          - Return "Invoice generated: {url}"
- This simplifies the "User Story 2: Warn" requirement. The tool reports existence, the LLM decides how to present it (e.g. "I found an existing invoice, here it is: ...").

### T012: Register Tool

- In `src/llm_client.py`:
  - Register `SendInvoiceTool`.
  - Ensure system prompt knows about it.

### T013: Update `WhatsAppService`

- In `src/whatsapp_service.py`:
- No major changes needed if we just pass the URL in text.
- Optional Polish: If the message body contains a URL ending in `.pdf`, try to send it as a media message instead of just text, or `media_url` parameter if using Twilio/WhatsApp API which supports it.

### T014: Integration Tests

- `tests/test_invoice_logic.py`.
- Test `SendInvoiceTool` finding a customer and calling service.
- Test `InvoiceService` works as expected.
- Mock the S3 upload to avoid network calls.

## Verification

- Run `pytest tests/test_invoice_logic.py`.
- End-to-end manual test: "Send invoice to John" -> Verify correct job picked, PDF generated, Link returned.

## Activity Log

- 2026-01-17T10:27:36Z – codex – lane=doing – Started implementation
- 2026-01-17T16:22:10Z – antigravity – lane=doing – Started implementation
- 2026-01-17T16:27:32Z – antigravity – lane=for_review – Implemented logic and tools
