# Feature Specification: Conversational Quotations

**Feature Branch**: `012-conversational-quotations`
**Created**: 2026-01-20
**Status**: Draft
**Mission**: software-dev
**Input**: User wants a quotation system where "send an invoice to John, clean 15 windows for 150$" creates a quote, looks up John, infers line items, and allows confirmation via text or website. Confirmation creates a Job.

## 1. Overview

The Conversational Quotations system allows business owners to send formal price proposals to customers using natural language. Unlike invoices (which bill for completed work), quotes represent a promise of service and price. Once a customer accepts a quote, the system automatically transitions it into an active, billable Job.

## 2. User Scenarios & Testing

### User Story 1 - Generate Quote from Natural Language (Priority: P1)

As a business owner, I want to say "send a quote to John for 10 windows at $50" and have the system generate a professional proposal automatically.

**Acceptance Scenarios**:

1. **Given** a customer "John" and a "Window Cleaning" service in the catalog ($5 default), **When** the user says "Send quote to John, clean 10 windows for $50", **Then** the system:
    - Identifies John's phone number.
    - Creates a Quote with a "Window Cleaning" line item (Qty 10, Unit Price $5, Total $50).
    - Generates a PDF/Link and sends it via the configured channel (WhatsApp/SMS).
2. **Given** ambiguous Johns, **When** "Send quote to John..." is requested, **Then** the system performs resolution (asking which John).

### User Story 2 - Customer Confirmation via Text (Priority: P1)

As a customer, I want to reply "Confirm" to a quote message to book the job immediately.

**Acceptance Scenarios**:

1. **Given** a Quote has been sent to a customer, **When** the customer replies "Confirm" or "Confirm invoice", **Then** the system:
    - Updates the Quote status to `ACCEPTED`.
    - Automatically creates a `Job` record for the customer with the line items from the quote.
    - Notifies the business owner that a new job has been booked.

### User Story 3 - Confirmation via External Website (Priority: P2)

As a business owner, I want the quote link to lead to a website where the customer can confirm, so the process feels professional.

**Acceptance Scenarios**:

1. **Given** a Quote link is clicked and the customer confirms on the external site, **When** the external site sends a callback/update to the CRM, **Then** the system transitions the Quote to `ACCEPTED` and creates a `Job` just like the text confirmation flow.

---

## 3. Requirements

### Functional Requirements

- **FR-001**: System MUST identify the target customer from natural language (Name/Phone) using existing lookup logic.
- **FR-002**: System MUST infer `LineItem`s from the request using the Service Catalog (Spec 004).
- **FR-003**: System MUST generate a unique `Quote` entity.
- **FR-004**: System MUST generate a professional PDF proposal (similar styling to Spec 006).
- **FR-005**: System MUST provide a public-facing URL for each quote (for the external confirmation website).
- **FR-006**: System MUST support status transitions: `DRAFT` -> `SENT` -> `ACCEPTED` / `REJECTED`.
- **FR-007**: System MUST automatically create a `Job` entity (Spec 001) upon a Quote moving to `ACCEPTED`.
- **FR-008**: System MUST support "Confirm" intent detection on incoming customer messages for active quotes.

### Key Entities

- **Quote**:
  - `id`: Unique ID.
  - `customer_id`: Link to Customer.
  - `line_items`: Collection of items (snapshot).
  - `total_amount`: Calculated sum.
  - `status`: [DRAFT, SENT, ACCEPTED, REJECTED, EXPIRED].
  - `external_link`: URL for the proposal website.
  - `job_id`: Reference to the Job created upon acceptance (optional).
- **Job**: (Existing) - will be created from Quote data.

---

## 4. Success Criteria

### Measurable Outcomes

- **SC-001**: Speed: A quote can be generated in under 3 seconds from a single text command.
- **SC-002**: Automation: 100% of "Confirm" replies on valid quotes result in a created Job record without manual intervention.
- **SC-003**: Accuracy: Line item inference matches Spec 004 precision (100% for clear "Qty + Total" inputs).

---

## 5. Assumptions & Risks

- **Assumption**: The external website for quote confirmation will communicate back to this CRM via an API endpoint or webhook to be defined.
- **Risk**: Overlapping quotes (sent multiple quotes to one customer) might make "Confirm" ambiguous if not handled by checking the most recent active quote.
- **Risk**: Text-based confirmation might be triggered by accident if the customer's "Confirm" refers to something else (mitigated by checking context/timeouts).
