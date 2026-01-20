# Quickstart: Conversational Quotations (012)

## Developer Setup

1. **Database Update**:
   - Run the upcoming Alembic migration to add `Quote` and `QuoteLineItem` tables.
2. **Environment**:
   - Ensure S3/Backblaze B2 credentials are set (reused from App 006).
   - Ensure `weasyprint` system dependencies are installed.

## Testing the Workflow

### 1. Generating a Quote via WhatsApp

Send a message to the CRM:
> "Send a quote to Alice (555-0101) for 10 windows at $5.50 each."

**Expected Result**:

- CRM replies with a PDF link or document.
- `Quote` record created with status `SENT`.

### 2. Confirming via Text

Reply to the message:
> "Confirm"

**Expected Result**:

- CRM replies: "Quote accepted! Job #123 has been created for you."
- `Quote` status -> `ACCEPTED`.
- `Job` record created with the same line items.

### 3. Confirming via Website

1. Get the `external_token` from the database.
2. Mock a POST request:

   ```bash
   curl -X POST http://localhost:8000/api/public/quotes/confirm \
     -H "Content-Type: application/json" \
     -d '{"token": "YOUR_TOKEN_HERE"}'
   ```

**Expected Result**:

- JSON response with `success: true` and `job_id`.
