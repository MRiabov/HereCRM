# Feature Specification: Multi-channel Communication

**Feature Branch**: `009-multi-channel-communication`  
**Created**: 2026-01-19  
**Status**: Draft  
**Input**: User description: "Add support for SMS (Twilio), Email (Postmark), and Generic Webhook channels. Includes User model refactoring for identity management and channel-specific configuration with auto-confirmation logic."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Multi-channel Engagement (Priority: P1)

A business can engage with customers across WhatsApp, SMS, and Email, using the most appropriate channel for each customer while maintaining a unified profile.

**Why this priority**: Core value proposition of the feature. Expands market reach beyond WhatsApp-dominant regions.

**Independent Test**: Can be tested by sending/receiving messages on all 3 channels to the same "User" entity.

**Acceptance Scenarios**:

1. **Given** a customer with a valid phone number, **When** the business answers via SMS, **Then** the message is sent via Twilio and the customer receives it.
2. **Given** a customer with a valid email, **When** the business answers via Email, **Then** the message is sent via Postmark and the customer receives an email.
3. **Given** a unified user profile, **When** messages come from different channels linked to that profile, **Then** they appear in the same conversation history (or are reasonably linked).

---

### User Story 2 - Cost-Efficient Confirmation (Priority: P1)

In expensive channels (SMS/Email), the system minimizes back-and-forth by auto-confirming pending actions if the user doesn't object.

**Why this priority**: Essential for cost control and UX on higher-latency/cost channels.

**Independent Test**: Verify the "45-second rule" logic in the state machine.

**Acceptance Scenarios**:

1. **Given** a pending tool action (e.g., "Create Job") on an SMS channel, **When** 45 seconds pass without user input, **Then** the action is automatically executed.
2. **Given** a pending tool action on SMS, **When** the user sends "Cancel" within 45 seconds, **Then** the action is aborted and no execution occurs.
3. **Given** a standard WhatsApp channel (default config), **When** a tool action is pending, **Then** it waits indefinitely for explicit confirmation (preserving existing behavior).

---

### User Story 3 - Integrations via Webhook (Priority: P2)

External systems (e.g., Zapier, Contact Forms) can inject messages or leads into the CRM via a generic webhook.

**Why this priority**: Enables flexibility and "catch-all" integration support.

**Independent Test**: Post a JSON payload to the new webhook endpoint and verify a registered message/lead.

**Acceptance Scenarios**:

1. **Given** a valid JSON payload sent to the generic webhook, **When** received, **Then** a new message/request is created in the system.
2. **Given** a payload with a known email/phone, **When** received, **Then** it is successfully linked to the existing user (if implemented) or creates a new one.

### Edge Cases

- **Concurrent Channel Usage**: User sends an SMS and an Email simultaneously. System should handle race conditions cleanly (likely sequential processing).
- **Identity Merging**: User starts on SMS, then emails. System might initially treat them as separate users unless an explicit "merge" or "link" feature exists (Out of scope for this MVP? Assumed separate unless matching handle provided). *Assumption: Matching by exact phone or email if provided.*
- **Invalid Channel Config**: System attempts to send SMS but Twilio config is missing. Should fail gracefully and log error.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support **TextGrid** as the *default* SMS provider for outbound/inbound SMS.
- **FR-001a**: System MUST maintain **Twilio** support as a configurable option (default disabled) using a common `SMSMessagingService` interface.
- **FR-002**: System MUST support **Postmark** for inbound/outbound Email (including threading logic).
- **FR-003**: System MUST provide a **Generic Webhook** endpoint accepting a standard JSON schema for inbound messages.
- **FR-004**: System MUST refactor the `User` model to use an **Integer ID** as the primary key, supporting `phone_number` and `email` as optional, unique, indexable fields.
- **FR-005**: System MUST support **per-channel configuration defaults** (YAML-based), specifically for `auto_confirm` behavior and timeouts.
- **FR-006**: System MUST implement an **Auto-Confirmation Strategy** where pending actions on configured channels (SMS/Email) execute automatically after a configurable timeout (default 45s) if no cancellation is received.
- **FR-007**: System MUST support **WhatsApp** via the existing Meta API integration (preserving current functionality).
- **FR-008**: System MUST allow configuring the "Max Message Length" or "conciseness" per channel (e.g., compact for SMS, standard for Email).
- **FR-009**: System MUST enforce **GSM-7 character set normalization** on all outbound SMS messages to prevent costly Unicode segmentation usage. Smart-replace emojis/special chars with ASCII equivalents where possible.

### Key Entities

- **User**: Refactored to have Integer ID, `email` (nullable), `phone` (nullable, but one is required).
- **ChannelConfig**: (Concept/File) Stores settings like `provider`, `auto_confirm_enabled`, `auto_confirm_timeout`, `max_length` for each channel type.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: SMS messages are sent/received via TextGrid (or Twilio) with < 2s internal processing latency.
- **SC-001a**: Default SMS configuration uses TextGrid to achieve ~6x cost reduction compared to Twilio.
- **SC-002**: Email messages are sent/received via Postmark with threading headers correctly maintained.
- **SC-003**: "Auto-confirm" actions execute successfully after the timeout window (±5s accuracy) without user intervention.
- **SC-004**: System handles concurrent inputs from different channels for the same user without data corruption.
