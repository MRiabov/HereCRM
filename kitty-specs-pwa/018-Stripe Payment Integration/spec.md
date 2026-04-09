# Feature Specification: Stripe Payment Integration

**Feature**: Stripe Payment Integration
**Status**: Draft
**Mission**: software-dev

## 1. Overview

This feature integrates **Stripe Connect** into the Whatsapp AI CRM to enable businesses to collect payments seamlessly. It facilitates a specific workflow where businesses (Tenants) can onboard via Stripe Standard Connect, generate professional invoices with embedded payment links, and track payment status automatically. The system leverages Stripe Hosted Checkout for security and simplicity, avoiding the need for a custom payment frontend.

## 2. Functional Requirements

### 2.0. Interface Structure
- **Chat-First UI**: The core experience mimics a chat application.
- **Side Menu**: A collapsible left-hand menu provides quick access to visual tools (e.g., Pipeline Board, Map View, Calendar, Settings).


### 2.1. Merchant Onboarding (Stripe Connect)

- **FR-001**: System MUST provide a mechanism for Business Owners to initiate Stripe onboarding (e.g., via a "setup payments" command or settings link).
- **FR-002**: System MUST generate a Stripe OAuth link (Standard Connect) that redirects the user to Stripe's onboarding flow.
- **FR-003**: System MUST handle the OAuth callback to securely retrieve and store the `stripe_connected_account_id` for the Business.
- **FR-004**: System MUST verify the account status (charges_enabled) before allowing payment link generation.

### 2.2. Business Settings for Compliance

- **FR-005**: System MUST allow Business Owners to configure "Official Business Details" separate from operation defaults:
  - Legal Business Name
  - Legal Address (Street, City, Zip, Country)
  - Tax/VAT ID
- **FR-006**: These details MUST be used on generated invoices for compliance.

### 2.3. Payment Link Generation

- **FR-007**: When an Invoice is generated (see `006-professional-invoices`), the system MUST create a corresponding Stripe Checkout Session.
  - **Mode**: Payment (one-time).
  - **Line Items**: Mapped from the Job details.
  - **Destination**: The connected Business account (Direct Charge).
- **FR-008**: The creation request MUST NOT include platform fees (application_fee_amount = 0).

### 2.4. Invoice & Message Enhancement

- **FR-009**: The generated PDF Invoice MUST include a clickable "Pay Now" link pointing to the Stripe Hosted Checkout page.
- **FR-010**: The WhatsApp message delivering the invoice MUST include the direct payment link in the text body (e.g., "Pay securely here: <https://stripe.com/>...").

### 2.5. Payment Status Tracking

- **FR-011**: System MUST expose a webhook endpoint to receive Stripe events (`connect` webhooks).
- **FR-012**: System MUST listen for `checkout.session.completed` events.
- **FR-013**: Upon successful payment, the system MUST:
  - Update the `Invoice` status to `PAID`.
  - Update the associated `Job` status to `PAID` (or equivalent).
  - Send a notification to the Business Owner: "Payment received for Job [ID] / Customer [Name]: [Amount]".

## 3. Data Model Enhancements

- **Business Entity**:
  - `stripe_account_id` (String, nullable): The connected Stripe Account ID (acct_...).
  - `legal_name` (String, nullable)
  - `legal_address` (JSON/String, nullable)
  - `tax_id` (String, nullable)

- **Invoice Entity**:
  - `stripe_session_id` (String, nullable): ID of the checkout session.
  - `payment_link` (String, nullable): The URL to the hosted checkout.
  - `status`: Update enum to include `PENDING_PAYMENT`, `PAID`, `VOID`.
  - `payment_date` (DateTime, nullable).

## 4. User Scenarios

### Scenario 1: Onboarding

1. **Owner** types: "Setup payments"
2. **System** displays: "Click here to connect your Stripe account and start accepting payments: [Link]"
3. **Owner** clicks link, completes Stripe form, and is redirected back.
4. **System** sends: "✅ Payments enabled! Your account is connected."

### Scenario 2: Sending a Payable Invoice

1. **Owner** types: "Send invoice to Sarah for Window Cleaning"
2. **System** identifies the job, generates Stripe Checkout link, creates PDF with link.
3. **System** displays: "Invoice sent to you. Forward this to Sarah:\n\n'Here is your invoice for Window Cleaning. You can pay securely online: [Stripe Link]'" and attaches the PDF.
4. **Sarah** clicks the link and pays.
5. **System** (via Webhook) detects payment.
6. **System** notifies Owner: "💰 Payment received! Sarah paid $50.00 for request #123."

### Scenario 3: Checking Payment Status

1. **Owner** types: "Who hasn't paid?"
2. **System** lists all Invoices with status `SENT` or `PENDING_PAYMENT`.

## 5. Success Criteria

- **SC-001**: Business can successfully link a Stripe account and receive a confirmation message.
- **SC-002**: Generated payment links successfully open a Stripe Checkout page with the correct amount and line items.
- **SC-003**: Payments made on Stripe automatically update the local database status to `PAID` within 1 minute (webhook latency).
- **SC-004**: PDF Invoices contain a valid, reachable URL for payment.

## 6. Assumptions & Risks

- **Stripe Availability**: Assumes businesses are in Stripe-supported regions.
- **Webhook Reliability**: Critical dependency on Stripe webhooks for status updates. Need to handle potential delivery failures (idempotency).
- **Compliance**: The platform (HereCRM) acts as a technology provider, not the merchant of record. The connected business is liable for refunds/disputes.
