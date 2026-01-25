# Implementation Plan - Feature 006: Professional Invoices

## User Review Required
>
> [!IMPORTANT]
> This feature introduces external S3 dependency (Backblaze B2). Requires valid API credentials in `.env`.

> [!NOTE]
> System library dependencies for `WeasyPrint` (e.g., `libpango`, `libcairo`) must be installed on the host/container.

## Proposed Changes

### Configuration

#### [MODIFY] .env.example / .env

- Add `S3_ENDPOINT_URL`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_BUCKET_NAME`.
- Add `S3_REGION_NAME` (optional).
- Add `STRIPE_SECRET_KEY` for Stripe Tax API integration.
- Add `STRIPE_TAX_ENABLED` (boolean flag, default: true).

### Infrastructure -> Services

#### [NEW] src/services/storage.py

- Implement `S3Service` class using `boto3`.
- Methods: `upload_file(file_obj, key)`, `get_public_url(key)`.

#### [NEW] src/services/pdf_generator.py

- Implement `InvoicePDFGenerator`.
- Use `jinja2` for HTML templating.
- Use `weasyprint` for PDF rendering.
- Method: `generate_invoice(job: Job) -> bytes`.

#### [NEW] src/templates/invoice.html

- Professional HTML/CSS template for invoices.

#### [NEW] src/services/tax_service.py

- Implement `StripeTaxService` class.
- Methods: `calculate_tax(line_items, customer_location, business_location, tax_mode)`.
- Handle both "Tax Included" and "Tax Added" modes.
- Implement caching for tax calculations.
- Graceful error handling with fallback to 0% tax.

### Data Model

#### [MODIFY] src/database/models.py

- Add `Invoice` SQLModel/SQLAlchemy model.
- Add tax fields to `Invoice`: `subtotal`, `tax_amount`, `tax_rate`, `total_amount`.
- Add `payment_link` field to `Invoice` (string, snapshot of business link).
- Add `tax_mode` field to `Business` model (Enum: "tax_included", "tax_added").
- Add `payment_link` field to `Business` model (string, optional).
- Update `Job` model with relationship.

### Core Logic

#### [NEW] src/services/invoice_service.py

- Business logic:
  - `create_invoice_for_job(job_id)`
  - Check for duplicates.
  - Orchestrate: Data Fetch -> Tax Calculation -> PDF Gen -> S3 Upload -> DB Save.
  - Integrate with `StripeTaxService` for tax calculation.
  - Fetch `payment_link` from `Business` and pass to `PDFGenerator` and include in metadata.

#### [MODIFY] src/tools/invoice_tools.py

- Define `SendInvoiceTool`.
- Logic: Find Customer -> Find Last Job -> Call `invoice_service`.
- Return a structured response that includes the PDF URL and the `payment_link`.

#### [MODIFY] src/uimodels.py

- Add `payment_link` to `ALLOWED_SETTING_KEYS` to enable configuration via conversational settings.

#### [MODIFY] src/llm_client.py

- Register `SendInvoiceTool`.

### API Exposure

- Expose Invoice management endpoints (List, Get) and generation actions for PWA.

### Integration

#### [MODIFY] src/whatsapp_service.py or src/services/messaging_service.py

- Programmatically handle the response from `SendInvoiceTool`.
- When an invoice is sent, the system MUST automatically construct the message to include the `payment_link` if available.
- Example logic: `message = f"Your invoice is attached. {f'Pay here: {payment_link}' if payment_link else ''}"`.
- This ensures the link is sent reliably alongside the file without relying on LLM text generation.

## Verification Plan

### Automated Tests

- `tests/test_invoice_generation.py`: Verify PDF bytes generated.
- `tests/test_storage_mock.py`: Verify S3 service places calls to boto3 (mocked).
- `tests/test_invoice_logic.py`: Verify duplicate prevention and job lookup.

### Manual Verification

1. Run server with S3 credentials.
2. Send WhatsApp message: "Send invoice to [Customer with Job]".
3. Verify:
    - "Generating..." status.
    - PDF document received.
    - Text link received.
    - Link opens correct PDF.
    - PDF looks professional.
4. Send same message again -> Verify warning "Invoice already exists".
