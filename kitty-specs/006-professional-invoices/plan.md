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

### Data Model

#### [MODIFY] src/database/models.py

- Add `Invoice` SQLModel/SQLAlchemy model.
- Update `Job` model with relationship.

### Core Logic

#### [NEW] src/services/invoice_service.py

- Business logic:
  - `create_invoice_for_job(job_id)`
  - Check for duplicates.
  - Orchestrate: Data Fetch -> PDF Gen -> S3 Upload -> DB Save.

#### [NEW] src/tools/invoice_tools.py

- Define `SendInvoiceTool`.
- Logic: Find Customer -> Find Last Job -> Call `invoice_service`.

#### [MODIFY] src/llm_client.py

- Register `SendInvoiceTool`.

### Integration

#### [MODIFY] src/whatsapp_service.py

- Handle the response from `SendInvoiceTool`.
- If response contains file path/URL, send appropriate message type (document + text).

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
