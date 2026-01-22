---
type: work-package
id: WP05
lane: "todo"
subtasks:
  - T026
  - T027
  - T028
  - T029
  - T030
  - T031
  - T032
---

# Work Package 05: Payment Link Integration

## Goal

Enable businesses to provide a custom payment link that is automatically included in generated PDF invoices and outgoing WhatsApp/SMS messages.

## Context

To streamline the payment process, businesses need a way to direct customers to their payment gateway (e.g., a Stripe Payment Link, PayPal.me link, or custom portal). This link should be prominent on the professional invoice and easily clickable in the notification message.

## Subtasks

### T026: Add `payment_link` field to `Business` model

- Modify `src/models.py` (or `src/database/models.py` depending on project structure).
- Add `payment_link: Mapped[Optional[str]] = mapped_column(String, nullable=True)` to the `Business` class.

### T027: Add `payment_link` snapshot to `Invoice` model

- Add `payment_link: Mapped[Optional[str]] = mapped_column(String, nullable=True)` to the `Invoice` class.
- This stores the link used at the time of invoice generation to ensure historical accuracy if the business changes their link later.

### T028: Database Migration

- Run `alembic revision --autogenerate -m "Add payment link to Business and Invoice"`.
- Run `alembic upgrade head`.

### T029: Update `invoice.html` template

- Modify `src/templates/invoice.html`.
- Add a "Pay Now" button or a clear payment section.
- Use conditional logic to only show the button if `invoice.payment_link` is present.
- Style the button to look professional and call-to-action oriented.

### T030: Update `InvoiceService`

- Modify `src/services/invoice_service.py`.
- When creating an invoice, fetch the `payment_link` from the associated `Business`.
- Save this link into the `Invoice` record.
- Pass the link to the `InvoicePDFGenerator`.

### T031: Update `SendInvoiceTool` and Messaging Logic

- Ensure `SendInvoiceTool` returns a structured response containing the `payment_link`.
- Update the messaging logic (in `src/services/whatsapp_service.py` or `src/services/messaging_service.py`) to **programmatically** append the payment link to the notification message.
- Do NOT rely on the LLM to include the link; the system code must ensure it is present if configured.
- Example: `Final Message = "Invoice attached. " + (f"Pay here: {link}" if link else "")`.

### T032: Verification Tests

- Add unit tests to verify `InvoiceService` correctly captures the payment link.
- Add integration tests to verify the payment link appears in the generated PDF (mocking the PDF content or checking the template rendering).
- Verify the WhatsApp message content includes the link when configured.

## Verification

- Manually set a `payment_link` for a test business.
- Trigger "Send invoice to [Customer]".
- Verify the link is in the message and the PDF.
