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

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST be able to identify the target customer from natural language (Name, Phone, or Address) using the existing Search/Lookup logic.
- **FR-002**: System MUST identify the *last performed job* for the target customer to invoice by default.
- **FR-003**: System MUST verify if an `Invoice` already exists for the selected Job. If yes, return a warning before proceeding.
- **FR-004**: System MUST generate a PDF file from the Job data ensuring professional formatting.
- **FR-005**: System MUST store the generated PDF using a persistent storage mechanism.
- **FR-006**: System MUST Create an `Invoice` entity linked to the Job upon successful generation.
- **FR-007**: System MUST be able to return a "Send" action (returning the link/file path to the chat interface).

### Key Entities

- **Invoice**: New entity.
  - `id`: Unique Identifier
  - `job`: Reference to Job (One-to-One)
  - `created_at`: Timestamp
  - `file_location`: Location/Link to the file
  - `status`: Status of the invoice (e.g., DRAFT, SENT)
- **Job**: Existing entity.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Efficiency: User can generate an invoice in **1 command** ("Send invoice to X") for the common case.
- **SC-002**: Safety: System warns **100% of the time** if an invoice already exists for the job.
- **SC-003**: Quality: Generated PDF allows for clear reading of line items and totals (Visual check).
- **SC-004**: Performance: PDF generation and delivery action takes under **60 seconds**.

## Assumptions

- "Sending" initially means returning the link/file to the chat context.
- The system will use a storage provider capable of retaining files permanently.
