---
type: work-package
id: WP03
lane: "doing"
review_status: "has_feedback"
reviewed_by: "antigravity"
subtasks:
  - T010
  - T011
  - T012
  - T013
  - T014
agent: "Antigravity"
---

## Review Feedback

**Status**: ❌ **Needs Changes**

**Key Issues**:

1. **File Organization Mismatch** - The task specification (T011) explicitly states to create `src/tools/invoice_tools.py` with the `SendInvoiceTool` class. However, the tool was instead added to `src/uimodels.py`. While this works functionally, it deviates from the planned architecture and makes the codebase harder to navigate. The `src/tools/` directory should contain tool implementations, not `uimodels.py`.

2. **Broad Exception Handling** - In `src/services/invoice_service.py` lines 43-45 and 55-57, there are broad `except Exception as e:` handlers. While they do log and re-raise, this is a code smell. These should catch specific exceptions (e.g., `PDFGenerationError`, `S3UploadError`, `boto3.exceptions.ClientError`) to provide better error handling and debugging.

3. **Tests Cannot Execute** - The integration tests in `src/tests/test_invoice_logic.py` cannot run because `boto3` is not installed in the virtual environment. This means the implementation has NOT been verified to work. The verification step in the task explicitly requires running `pytest tests/test_invoice_logic.py`, which currently fails.

4. **Missing Optional Enhancement** - T013 mentions "Optional Polish: If the message body contains a URL ending in `.pdf`, try to send it as a media message instead of just text". This wasn't implemented, but since it's marked as "Optional", it's not a blocker.

**What Was Done Well**:

- ✅ `InvoiceService` is well-structured with clear separation of concerns (PDF generation, S3 upload, DB storage)
- ✅ `SendInvoiceTool` is properly integrated into `ToolExecutor` with correct customer search and job lookup logic
- ✅ Tool is registered in `llm_client.py` correctly
- ✅ WhatsApp service integration includes proper summary generation for the tool
- ✅ Tests are comprehensive and cover success cases, error cases, and existing invoice warnings
- ✅ Security checks passed: no shell=True, no SQL injection patterns, no TODOs/mocks in production code
- ✅ Invoice model matches spec requirements with all required fields

**Action Items** (must complete before re-review):

- [ ] **CRITICAL**: Create `src/tools/invoice_tools.py` and move `SendInvoiceTool` from `src/uimodels.py` to this new file as specified in T011
- [ ] **CRITICAL**: Update all imports to reference the new location (`from src.tools.invoice_tools import SendInvoiceTool`)
- [ ] **CRITICAL**: Replace broad exception handlers in `invoice_service.py` with specific exception types (e.g., catch `boto3.exceptions.ClientError` for S3 operations)
- [ ] **CRITICAL**: Install dependencies in the venv by running `pip install -e .` or `uv sync` from the project root
- [ ] **CRITICAL**: Run `pytest src/tests/test_invoice_logic.py -v` and verify all tests pass
- [ ] Optional: Implement PDF media message sending in WhatsApp service (T013 optional enhancement)

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
- 2026-01-17T16:32:47Z – antigravity – shell_pid=3203448 – lane=planned – Code review complete: File organization mismatch (tool in wrong location), broad exception handlers, tests cannot run due to missing boto3
- 2026-01-17T20:59:21Z – Antigravity – shell_pid= – lane=doing – Started implementation
