# 015 - Ad Automation & Integrations

## 1. Overview

This feature introduces a secure integration layer to HereCRM, enabling automated data ingestion (from ads) and conversion reporting (to ads). It eliminates manual data entry for new leads and closes the loop on ad performance by reporting "Booked" jobs back to ad platforms.

## 2. Goals

1. **Automate Ingestion**: Provide secure API endpoints to programmatically create Leads and Requests from external sources (e.g., Zapier, Landing Pages).
2. **Meta CAPI Integration**: Native backend integration with Facebook/Meta Conversions API to report "Booked" jobs as conversions.
3. **Universal Webhooks**: A generic outbound webhook system to notify external tools (Zapier, etc.) when key business events occur.

## 3. User Stories

- **As a Marketer**, I want leads from Facebook/Google Forms to instantly appear in HereCRM so the sales team can contact them immediately.
- **As a Business Owner**, I want `Job Booked` events to be sent back to Facebook Ads so the algorithm optimizes for paying customers, not just leads.
- **As an Integrator**, I want to subscribe to a `job.booked` webhook so I can trigger custom workflows (e.g., send a welcome packet, update Google Sheets) without modifying HereCRM code.

## 4. Functional Requirements

### 4.1 Authentication Base

- **API Keys**: All external endpoints must be protected by an API Key authentication scheme (e.g., `X-API-Key` header).

- **Key Validation**: Middleware must reject requests with invalid or missing keys.

### 4.2 Inbound API

- **Create Lead**: `POST /api/v1/integrations/leads`
  - **Input**: `name` (required), `phone` (required), `email` (optional), `source` (optional).
  - **Output**: JSON with created Customer ID.
  - **Logic**: Checks if customer exists by phone; if not, creates new.

- **Create Request**: `POST /api/v1/integrations/requests`
  - **Input**: Customer info (same as above), `address`, `service_type`, `notes`.
  - **Output**: JSON with created Request ID.
  - **Logic**: Creates customer (if needed), then creates a Service Request linked to them.

### 4.3 Outbound Event Engine

- **Core Event**: The system must detect when a Job transitions to a `BOOKED` state.

- **Dispatcher**: A background task or service method should handle the dispatching of events to configured handlers (Meta, Webhooks) asynchronously to avoid blocking user interactions.

### 4.4 Meta Conversions API (CAPI) Integration

- **Configuration**: Needs `META_PIXEL_ID` and `META_ACCESS_TOKEN` (sys_params or env vars).

- **Event Map**: Map `Job Booked` -> CAPI `Schedule` event.
- **Data Hashing**: User data (email, phone) MUST be normalized and hashed (SHA-256) per Meta's strict privacy requirements before sending.
- **Payload**: Include `event_time`, `user_data` (hashed), `custom_data` (value, currency).

### 4.5 Generic Webhooks

- **Configuration**: Support a list of destination URLs for the `job.booked` event (stored in DB or simple config).

- **Payload**: Standard JSON payload describing the job (ID, Customer Name, Service Type, Price).
- **Security**: Include a signature header (`X-HereCRM-Signature`) generated via HMAC-SHA256 using a shared secret, allowing receivers to verify authenticity.

### 4.6 Edge Cases

* **Invalid/Expired API Key**: Request is denied with 401 Unauthorized.
- **Duplicate Customer**: If a lead matches an existing phone number, update the existing record or log a note (do not create duplicate).
- **External Service Failure**: If Meta CAPI or a Webhook endpoint is down (500/timeout), the system logs the failure without crashing the main transaction. Retry logic is out of scope for MVP but failure must be visible.
- **Missing Data**: If a booked job lacks a customer email/phone (rare), the Meta event is sent with minimal data (or skipped with a warning log), as PII is required for matching.

## 5. Non-Functional Requirements

* **Performance**: Webhook dispatch must not increase the latency of the "Book Job" user action.
- **Reliability**: Failure to send a webhook should be logged but shouldn't rollback the database transaction.
- **Security**: API Keys must be long-ended random strings. Verification must use constant-time comparison to prevent timing attacks.

## 6. Success Criteria

1. **Seamless Ingestion**: A third-party system can successfully create a new Lead in the CRM using only a standard HTTP client and valid API Key.
2. **Verifiable Reporting**: The system successfully emits a "Schedule" event to the configured Meta endpoint whenever a job enters the 'Booked' state.
3. **Secure Handoff**: A 3rd-party webhook receiver can cryptographically verify that a "Job Booked" notification originated from HereCRM using the provided signature.
