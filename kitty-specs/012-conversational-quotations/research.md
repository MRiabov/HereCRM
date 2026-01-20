# Research: Conversational Quotations (012)

## Decisions

### Decision 1: PDF Generation Refactoring

- **Choice**: Refactor `src/services/pdf_generator.py` to use a base class or common utilities for shared logic (Jinja2 setup, storage interaction).
- **Rationale**: Both Invoices and Quotes share the same template-to-S3 pipeline.
- **Alternatives**: Copy-paste logic into `QuotePDFGenerator`. (Rejected: violates DRY).

### Decision 2: Quote Confirmation Security

- **Choice**: Use a cryptographically secure random token (UUID4 or similar) stored in the `Quote` record.
- **Rationale**: User Story 3 requires a link for external confirmation. A token in the URL allows the external site to authenticate the request back to the CRM without full user login.
- **Implementation**: `external_token` field in `Quote` model. URL: `https://here-crm-website.com/confirm?token={token}`.

### Decision 3: Ambiguity Resolution for Text Confirmation

- **Choice**: Implicitly confirm the most recent `SENT` quote for the customer.
- **Rationale**: User confirmed this preference. Reduces friction for the customer.
- **Implementation**: Query `Quote` table filtered by `customer_id` and `status=SENT`, order by `created_at DESC`, take first.

### Decision 4: Automatic Job Creation

- **Choice**: Reuse `JobService` to create a new Job record.
- **Rationale**: Ensures consistency with existing Job creation logic (Spec 001).
- **Mapping**: `Quote.line_items` -> `Job.line_items`.

## Dependencies & Patterns

### WeasyPrint Integration

Existing pattern from Spec 006 is stable. Will continue using `libpango` on the host.

### S3 Service Interaction

Will utilize the `S3Service` from `src/services/storage.py` (implemented in Spec 006).

## API Contract (Internal/Public)

- `POST /api/public/quotes/confirm`: Receives `{ token: string }`.
- Logic: Find quote -> Validate -> Transition status -> Create Job -> Return success.
