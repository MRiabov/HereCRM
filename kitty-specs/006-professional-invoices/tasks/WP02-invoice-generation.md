---
type: work-package
id: WP02
lane: "for_review"
subtasks:
  - T007
  - T008
  - T009
agent: "Antigravity"
review_status: "has_feedback"
reviewed_by: "Antigravity"
---

## Review Feedback

**Status**: ❌ **Needs Changes**

**Key Issues**:

1. **CRITICAL SECURITY: Template Injection Vulnerability** - The Jinja2 `Environment` is created without `autoescape=True`, which means user-controlled data (customer names, addresses, line item descriptions) will NOT be HTML-escaped. This allows malicious input like `<script>alert('XSS')</script>` or Jinja2 template injection attacks to execute. This is a **BLOCKER** security issue.

2. **Missing Error Handling** - The `generate()` method has NO exception handling for:
   - Template loading failures (`get_template()` can raise `TemplateNotFound`)
   - Template rendering failures (Jinja2 can raise various exceptions if data is malformed)
   - PDF generation failures (`weasyprint.HTML().write_pdf()` can fail due to CSS issues, missing fonts, or invalid HTML)

   If any of these fail, the entire service crashes with an unhelpful stack trace instead of returning a meaningful error message.

3. **Linting Issue** - `tests/test_invoice_generation.py` imports `pytest` but never uses it. This should be removed to maintain clean code standards.

**What Was Done Well**:

- ✅ Professional HTML template design with clean CSS styling
- ✅ Proper Jinja2 variable syntax and conditional rendering for optional fields
- ✅ Tests actually verify PDF generation (check for PDF magic bytes)
- ✅ Tests cover both with and without optional date parameter
- ✅ No TODOs, FIXMEs, or mocked implementations in production code
- ✅ Clean separation of concerns (template, generator service, tests)
- ✅ Good use of `pathlib` alternatives (`os.path`) for cross-platform compatibility

**Action Items** (must complete before re-review):

- [ ] **FIX SECURITY**: Update `InvoicePDFGenerator.__init__()` to create Jinja2 environment with `autoescape=True`:

  ```python
  self.env = Environment(
      loader=FileSystemLoader(template_dir),
      autoescape=True  # CRITICAL: Prevent template injection
  )
  ```

- [ ] **ADD ERROR HANDLING**: Wrap template operations in try/except blocks with specific exceptions:

  ```python
  try:
      template = self.env.get_template(self.template_name)
      html_content = template.render(**context)
      pdf_bytes = HTML(string=html_content).write_pdf()
      return pdf_bytes
  except TemplateNotFound as e:
      raise ValueError(f"Invoice template not found: {self.template_name}") from e
  except Exception as e:
      raise RuntimeError(f"Failed to generate invoice PDF: {str(e)}") from e
  ```

- [ ] **FIX LINTING**: Remove unused `import pytest` from `tests/test_invoice_generation.py`

- [ ] **ADD ERROR HANDLING TEST**: Create a test that verifies graceful failure when template is missing or rendering fails

- [ ] **VERIFY SECURITY FIX**: After enabling autoescape, create a test with malicious input (e.g., customer name with `<script>` tags) and verify it's escaped in the PDF

# Work Package 02: Invoice PDF Generation

## Goal

Implement the core business logic for generating professional PDF invoices from Job data using HTML templates.

## Context

We need to generate "Professional" looking invoices. We will use `jinja2` to render an HTML template with dynamic Job/Customer data, and `weasyprint` to convert that HTML to a PDF.

## Subtasks

### T007: Create HTML Template

- Create `src/templates/invoice.html`.
- Design a clean, professional layout using internal CSS.
- Sections:
  - Header: Business Name/Logo (placeholder), "Invoice" title.
  - Info: Invoice # (Job ID), Date, Customer Name, Customer Address (if avail).
  - Table: Description, Quantity, Price, Total.
  - Footer: Business Contact Info, Total Amount Due.
- Use Jinja2 syntax for variables (e.g., `{{ job.customer.name }}`, `{{ line_item.price }}`).

### T008: Implement `InvoicePDFGenerator`

- Create `src/services/pdf_generator.py`.
- Class `InvoicePDFGenerator`:
  - `__init__`: Setup jinja2 environment pointing to `src/templates`.
  - `generate(job: Job, invoice_number: str) -> bytes`:
    - Prepare context dict from `Job` object.
    - Render template to string.
    - Use `weasyprint.HTML(string=...).write_pdf()` to get bytes.
- Handle styling assets if necessary (prefer inline CSS for simplicity).

### T009: PDF Generation Tests

- Create `tests/test_invoice_generation.py`.
- Test `generate` method:
  - Mock a `Job` object with `LineItems`.
  - assertion: Output is not empty.
  - assertion: Output starts with PDF magic bytes (`%PDF`).
- Optional: Verify content matches (hard with binary, trust visual check for now).

## Verification

- Run `pytest tests/test_invoice_generation.py`.
- Create a temporary script to generate a PDF for a dummy job and save it to disk -> Open it manually to check visuals (attach screenshot to walkthrough).

## Activity Log

- 2026-01-17T10:09:23Z – Antigravity – lane=doing – Started implementation
- 2026-01-17T10:20:48Z – Antigravity – lane=for_review – Ready for review - PDF generation implemented and verified
- 2026-01-17T10:27:44Z – Antigravity – shell_pid=3066190 – lane=planned – Code review rejected: Critical security vulnerability (template injection - missing autoescape), missing error handling for template/PDF operations, linting issue (unused import). Tests pass but implementation needs security fixes before approval.
- 2026-01-17T10:33:24Z – Antigravity – lane=doing – Addressing reviewer feedback
- 2026-01-17T10:43:03Z – Antigravity – lane=for_review – Addressed review feedback: Fixed security vulnerability and added error handling.
