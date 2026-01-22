---
type: work-package
id: WP06
lane: "planned"
subtasks:
  - T024
  - T025
  - T026
  - T027
  - T028
  - T029
  - T030
  - T031
  - T032
  - T033
agent: ""
review_status: ""
reviewed_by: ""
---

# Work Package 06: Tax Calculation Integration

## Goal

Integrate Stripe Tax API for accurate tax calculation on quotes. Ensure tax data is preserved when converting accepted quotes to jobs. Support both "Tax Included" and "Tax Added" pricing modes configured at the business level.

## Context

Quotes need accurate tax calculation just like invoices. We'll reuse the `StripeTaxService` from spec 006. Tax calculations must be preserved when a quote is accepted and converted to a job. This ensures consistency between the quoted price and the final invoice.

## Prerequisites

- Spec 006 WP04 (Tax Calculation Integration) must be complete, as we're reusing `StripeTaxService`.
- Business model must have `tax_mode` field (added in spec 006 WP04).

## Subtasks

### T024: Reuse StripeTaxService from spec 006

- Verify `src/services/tax_service.py` exists and `StripeTaxService` is implemented.
- Import and use `StripeTaxService` in `QuoteService`.
- No new implementation needed; this is a verification task.

### T025: Add tax fields to Quote model

- In `src/database/models.py`, update `Quote` class.
- Add fields:
  - `subtotal: Decimal` (amount before tax)
  - `tax_amount: Decimal` (calculated tax)
  - `tax_rate: Decimal` (tax rate percentage)
  - `total_amount: Decimal` (final amount, replaces existing `total_amount` if present)
- Ensure proper decimal precision (e.g., `Decimal(10, 2)`).

### T026: Create Alembic Migration

- Run `alembic revision --autogenerate -m "Add tax fields to Quote model"`.
- Inspect the generated migration file.
- Handle existing `total_amount` field if it exists (may need data migration).
- Run `alembic upgrade head`.

### T027: Update QuoteService.create_quote to integrate tax calculation

- In `src/services/quote_service.py`, update `create_quote` method.
- Before generating PDF:
  1. Fetch business and customer location data.
  2. Call `StripeTaxService.calculate_tax()` with quote line items.
  3. Store tax calculation results in the Quote model fields.
- Update the orchestration flow to include tax calculation step.

### T028: Update QuoteService.confirm_quote to preserve tax data

- In `src/services/quote_service.py`, update `confirm_quote` method.
- When creating a Job from an accepted Quote:
  - Transfer tax data from Quote to Job (if Job model has tax fields).
  - If Job doesn't have tax fields yet, ensure the invoice generated from the Job uses the same tax calculation.
  - Document the tax preservation strategy in code comments.

### T029: Update quote HTML template

- In `src/templates/quote.html`, add tax breakdown section.
- Display:
  - Subtotal
  - Tax rate (e.g., "Sales Tax (8.5%)")
  - Tax amount
  - Grand total
- Ensure formatting matches invoice template for consistency.
- Handle both "tax_included" and "tax_added" modes in the display.

### T030: Implement tax recalculation when quote line items are modified

- If there's a method to edit quote line items before sending (e.g., `update_quote_items`):
  - Recalculate taxes after line item changes.
  - Update Quote model tax fields.
- If no such method exists, document that tax is calculated once at creation and note this as a future enhancement.

### T031: Add unit tests for quote tax calculation

- Create or update `tests/test_quote_tax.py`.
- Test cases:
  - Quote creation with "tax_added" mode.
  - Quote creation with "tax_included" mode.
  - Tax calculation error handling (fallback to 0% tax).
  - Tax data is correctly stored in Quote model.
- Mock Stripe API calls.

### T032: Add integration tests for quote-to-job tax preservation

- Create or update `tests/test_quote_to_job.py`.
- Test full flow:
  1. Create a Quote with tax calculation.
  2. Accept the Quote (trigger `confirm_quote`).
  3. Verify the created Job has correct tax data or can generate an invoice with matching tax.
- Mock S3 and Stripe API calls.

### T033: Handle tax calculation errors gracefully

- In `QuoteService.create_quote`, wrap tax calculation in try-except.
- If `StripeTaxService.calculate_tax()` fails:
  - Log a warning with error details.
  - Set tax fields to 0% (subtotal = total_amount, tax_amount = 0, tax_rate = 0).
  - Continue with quote generation.
- Add test case for this error scenario.

## Verification

- All unit tests pass for quote tax calculation.
- Integration tests pass for quote-to-job tax preservation.
- Manual test: Create a quote with real Stripe credentials and verify tax calculation is accurate.
- Verify quote PDF displays tax breakdown correctly.
- Verify both "tax_included" and "tax_added" modes work as expected.
- Verify accepted quote creates a job with correct tax data.

## Dependencies

- Requires spec 006 WP04 (Tax Calculation Integration) to be complete.
- Requires WP01 (Foundation & Core Service) to be complete.
- Requires WP02 (PDF Generation & Delivery) to be complete for template updates.
- Requires WP04 (Confirmation Workflow) to be complete for quote-to-job conversion.

## Notes

- Tax calculation on quotes should be identical to invoices for consistency.
- Consider adding a "Recalculate Tax" button in the UI if quotes can be edited before sending.
- If customer location changes after quote creation, taxes may be inaccurate. Document this limitation.
- Tax preservation from quote to job is critical for customer trust and legal compliance.

## Activity Log

<!-- Agent will log activities here during implementation -->
