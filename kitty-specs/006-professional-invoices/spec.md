# Feature Specification: Professional Invoices

**Feature Branch**: `006-professional-invoices`
**Created**: 2026-01-17
**Status**: Draft
**Input**: User wants professional PDF invoices sent via WhatsApp/SMS/Email, preventing duplicates, defaulting to the last job.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Send Invoice for Last Job (Priority: P1)

As a user, I want to quickly generate and send an invoice for the most recent job completed for a customer so that I can get paid without manual data entry.

**Why this priority**: This is the primary "happy path" workflow.

**Independent Test**: Simulate chat command "Send invoice to [Customer]" and verify PDF generation + message output.

**Acceptance Scenarios**:

1. **Given** a customer "John" with a completed job ($100, pending invoice), **When** user says "Send invoice to John", **Then** system finds the job, generates a professional PDF, saves it, and returns a WhatsApp message with the PDF and/or link.
2. **Given** multiple customers named "John", **When** user says "Send invoice to John", **Then** system asks for clarification or lists options.
3. **Given** no recent job for "John", **When** user says "Send invoice to John", **Then** system responds that no billable job was found.

---

### User Story 2 - Prevent Duplicate Invoices (Priority: P2)

As a business owner, I want to be warned if I try to send an invoice for a job that has already been invoiced so that I don't look unprofessional or confuse the customer.

**Why this priority**: Essential for business professionalism and data integrity.

**Independent Test**: Attempt to generate an invoice twice for the same job.

**Acceptance Scenarios**:

1. **Given** a job that already has an associated Invoice record, **When** user tries to "Send invoice" again, **Then** system warns "Invoice already exists sent on [Date]" and asks for confirmation to resend or regenerate.

---

### User Story 3 - Professional PDF Styling (Priority: P2)

As a business owner, I want the invoices to look professional (clean layout, logo placeholders) so that my business looks reputable.

**Why this priority**: User explicitly requested "very professional" look.

**Independent Test**: Visual inspection of the generated PDF.

**Acceptance Scenarios**:

1. **Given** a job with line items, **When** invoice is generated, **Then** the PDF contains Business Name, Customer Details, Line Item Table, Total, and Date, formatted cleanly (e.g., HTML/CSS template converted to PDF).

---

### User Story 4 - Custom Payment Link (Priority: P2)

As a business owner, I want to add my own payment link (Stripe, PayPal, etc.) to my invoices so that my customers can pay me easily online.

**Why this priority**: Improves cash flow for the business and convenience for the customer.

**Independent Test**: Configure a payment link for a business, generate an invoice, and verify the link appears in the PDF and message.

**Acceptance Scenarios**:

1. **Given** a business with a configured payment link "https://stripe.com/pay/abc", **When** an invoice is generated, **Then** the PDF contains a "Pay Now" button/link and the WhatsApp message includes the link.
2. **Given** a business with NO payment link configured, **When** an invoice is generated, **Then** no payment button appears in the PDF and no link is sent in the message.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST be able to identify the target customer from natural language (Name, Phone, or Address) using the existing Search/Lookup logic.
- **FR-002**: System MUST identify the *last performed job* for the target customer to invoice by default.
- **FR-003**: System MUST verify if an `Invoice` already exists for the selected Job. If yes, return a warning before proceeding.
- **FR-004**: System MUST generate a PDF file from the Job data ensuring professional formatting.
- **FR-005**: System MUST store the generated PDF using a persistent storage mechanism.
- **FR-006**: System MUST Create an `Invoice` entity linked to the Job upon successful generation.
- **FR-007**: System MUST be able to return a "Send" action (returning the link/file path to the chat interface).
- **FR-008**: System MUST allow a Business to store a `payment_link` in their settings.
- **FR-009**: System MUST include a prominent "Pay Now" button in the PDF invoice if `payment_link` is configured.
- **FR-010**: System MUST include the `payment_link` in the WhatsApp/SMS message sent along with the invoice.
- **FR-011**: System MUST allow configuring the `payment_link` via the conversational Settings interface.

### Key Entities

- **Invoice**: New entity.
  - `id`: Unique Identifier
  - `job`: Reference to Job (One-to-One)
  - `created_at`: Timestamp
  - `file_location`: Location/Link to the file
  - `status`: Status of the invoice (e.g., DRAFT, SENT)
  - `payment_link`: Snapshot of the payment link used for this invoice.
- **Job**: Existing entity.
- **Business**: Existing entity.
  - `payment_link`: URL for customer payments.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Efficiency: User can generate an invoice in **1 command** ("Send invoice to X") for the common case.
- **SC-002**: Safety: System warns **100% of the time** if an invoice already exists for the job.
- **SC-003**: Quality: Generated PDF allows for clear reading of line items and totals (Visual check).
- **SC-004**: Performance: PDF generation and delivery action takes under **60 seconds**.

## Tax Calculation

### Overview

Invoices must accurately calculate and display applicable taxes using the Stripe Tax API. The system will query Stripe Tax to determine the correct tax rates based on the business location, customer location, and service type.

### Business Settings

Businesses can configure how taxes are applied to their pricing:

- **Tax Application Mode**: Toggle between "Tax Included" and "Tax Added"
  - **Tax Included**: The price shown to customers already includes tax (tax is calculated backwards from the total)
  - **Tax Added**: Tax is calculated and added on top of the stated price
  - This setting is stored in the `Business` model as `tax_mode` field

### Tax Functional Requirements

- **FR-TAX-001**: System MUST integrate with Stripe Tax API to calculate accurate tax amounts
- **FR-TAX-002**: System MUST respect the business's `tax_mode` setting when calculating totals
- **FR-TAX-003**: System MUST display tax breakdown on invoices (tax rate, tax amount, subtotal, total)
- **FR-TAX-004**: System MUST handle tax calculation errors gracefully (fallback to 0% tax with warning)
- **FR-TAX-005**: System MUST cache tax calculations to avoid redundant API calls for identical line items

### Tax Display

Invoices must clearly show:

- Subtotal (before tax for "Tax Added" mode, or net amount for "Tax Included" mode)
- Tax rate(s) applied
- Tax amount
- Grand total

## Assumptions & Dependencies

- "Sending" initially means returning the link/file to the chat context.
- The system will use a storage provider capable of retaining files permanently.
- Stripe Tax API credentials are configured and valid.
- Business and customer location data is accurate for tax calculation purposes.
