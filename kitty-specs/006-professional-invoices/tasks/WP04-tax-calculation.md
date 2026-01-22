---
type: work-package
id: WP04
lane: "planned"
subtasks:
  - T015
  - T016
  - T017
  - T018
  - T019
  - T020
  - T021
  - T022
  - T023
  - T024
  - T025
agent: ""
review_status: ""
reviewed_by: ""
---

# Work Package 04: Tax Calculation Integration

## Goal

Integrate Stripe Tax API to automatically calculate accurate taxes on invoices based on business location, customer location, and service type. Support both "Tax Included" and "Tax Added" pricing modes.

## Context

Businesses need accurate tax calculation on invoices. We'll use Stripe Tax API to query tax rates dynamically. The business can configure whether their stated prices include tax or have tax added on top. This work package adds the tax service, updates data models, and integrates tax calculation into the invoice generation flow.

## Subtasks

### T015: Install Stripe Python SDK

- Add `stripe` to `pyproject.toml` dependencies.
- Run `uv sync` or equivalent to install.
- Verify installation: `python -c "import stripe; print(stripe.__version__)"`.

### T016: Add Stripe Configuration

- Update `.env.example` with:
  - `STRIPE_SECRET_KEY` (required for Stripe Tax API)
  - `STRIPE_TAX_ENABLED` (boolean, default: true)
- Add these fields to `Settings` class in `src/config.py`.
- Ensure the Stripe SDK is initialized with the secret key on application startup.

### T017: Implement `StripeTaxService`

- Create `src/services/tax_service.py`.
- Class `StripeTaxService`:
  - `__init__(self, stripe_api_key: str, enabled: bool = True)`
  - `calculate_tax(line_items: List[LineItem], customer_location: dict, business_location: dict, tax_mode: str) -> TaxCalculation`:
    - For "tax_added" mode: Calculate tax on the stated prices and return subtotal, tax_amount, tax_rate, total.
    - For "tax_included" mode: Calculate the net amount (price excluding tax) and return subtotal (net), tax_amount, tax_rate, total (original price).
    - Use Stripe Tax API: `stripe.tax.Calculation.create()` with appropriate parameters.
    - Handle API errors gracefully: if Stripe fails, log warning and return 0% tax with original amounts.
  - Implement caching mechanism (simple in-memory dict or Redis) to avoid redundant API calls for identical line items.
- Define `TaxCalculation` dataclass/Pydantic model with fields: `subtotal`, `tax_amount`, `tax_rate`, `total_amount`.

### T018: Add `tax_mode` field to Business model

- In `src/database/models.py`, update `Business` class.
- Add field: `tax_mode: str` (Enum or string with values: "tax_included", "tax_added", default: "tax_added").
- Consider using SQLModel Enum or a simple string field with validation.

### T019: Add tax fields to Invoice model

- In `src/database/models.py`, update `Invoice` class.
- Add fields:
  - `subtotal: Decimal` (amount before tax)
  - `tax_amount: Decimal` (calculated tax)
  - `tax_rate: Decimal` (tax rate percentage, e.g., 8.5 for 8.5%)
  - `total_amount: Decimal` (final amount)
- Ensure proper decimal precision (e.g., `Decimal(10, 2)`).

### T020: Create Alembic Migration

- Run `alembic revision --autogenerate -m "Add tax fields to Business and Invoice models"`.
- Inspect the generated migration file.
- Ensure default values are set appropriately (e.g., `tax_mode` defaults to "tax_added").
- Run `alembic upgrade head`.

### T021: Update InvoiceService to integrate tax calculation

- In `src/services/invoice_service.py`, update `create_invoice_for_job` method.
- Before generating PDF:
  1. Fetch business and customer location data.
  2. Call `StripeTaxService.calculate_tax()` with job line items.
  3. Store tax calculation results in the Invoice model fields.
- Update the orchestration flow: Data Fetch -> Tax Calculation -> PDF Gen -> S3 Upload -> DB Save.

### T022: Update invoice HTML template

- In `src/templates/invoice.html`, add tax breakdown section.
- Display:
  - Subtotal
  - Tax rate (e.g., "Sales Tax (8.5%)")
  - Tax amount
  - Grand total
- Ensure formatting is professional and clear.
- Handle both tax modes appropriately in the display.

### T023: Add unit tests for StripeTaxService

- Create `tests/test_tax_service.py`.
- Mock Stripe API calls using `unittest.mock` or `pytest-mock`.
- Test cases:
  - Tax calculation in "tax_added" mode.
  - Tax calculation in "tax_included" mode.
  - API error handling (fallback to 0% tax).
  - Caching behavior (second call with same params doesn't hit API).
- Verify correct calculation of subtotal, tax_amount, tax_rate, total_amount.

### T024: Add integration tests for invoice generation with tax

- Create or update `tests/test_invoice_integration.py`.
- Test full invoice generation flow with tax calculation:
  - Create a Job with line items.
  - Set business `tax_mode` to "tax_added".
  - Generate invoice and verify tax fields are populated correctly.
  - Repeat with "tax_included" mode.
- Mock S3 and Stripe API calls.

### T025: Implement tax calculation caching

- In `StripeTaxService`, implement a simple cache (dict or LRU cache).
- Cache key: hash of (line_items, customer_location, business_location, tax_mode).
- Cache value: `TaxCalculation` result.
- Set reasonable TTL (e.g., 1 hour) or cache size limit.
- Add test to verify cache hit reduces API calls.

## Verification

- All unit tests pass for `StripeTaxService`.
- Integration tests pass for invoice generation with tax.
- Manual test: Generate an invoice with real Stripe credentials (if available) and verify tax calculation is accurate.
- Verify invoice PDF displays tax breakdown correctly.
- Verify both "tax_included" and "tax_added" modes work as expected.

## Dependencies

- Requires WP01 (Infrastructure & Data Model) to be complete.
- Requires WP02 (Invoice PDF Generation) to be complete for template updates.
- Requires WP03 (Logic, Tools & Integration) to be complete for InvoiceService updates.

## Notes

- Stripe Tax API requires valid business and customer location data (address, country, postal code).
- Ensure location data is available in the Business and Customer models before implementing this WP.
- If location data is missing, consider adding it as part of this WP or a prerequisite.
- Tax calculation errors should not block invoice generation; fallback to 0% tax with a warning.

## Activity Log

<!-- Agent will log activities here during implementation -->
