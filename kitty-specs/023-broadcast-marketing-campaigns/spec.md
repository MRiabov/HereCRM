# 023 Broadcast Marketing Campaigns

## Goal

Enable business owners to send proactive mass messages (broadcasts) to specific customer segments via Email and WhatsApp, shifting the CRM from reactive to proactive revenue generation.

## Problem Statement

Currently, the CRM is reactive (managing incoming work). Owners have no tools to generate work on demand (e.g., filling a quiet Friday). They need a way to target specific groups (e.g., "Dublin customers") with promotions, but safety is critical to avoid accidental mass-spamming.

## User Scenarios

### 1. The "Slow Week" Filler

**User**: Business Owner
**Context**: It's Wednesday, and Friday schedule is empty.
**Action**: User types: "Send a Whatsapp to all customers in Dublin who we did Gutter Cleaning for: '20% off this Friday only!'"
**System Response**:

1. Analyzes query: `Location=Dublin`, `Service=Gutter Cleaning`.
2. Finds 42 matching customers.
3. Drafts message.
4. Pauses and shows "Blast Report": "Targeting 42 customers. Channel: WhatsApp. Cost estimate: $X."
5. Requires typed confirmation: "CONFIRM BLAST".
**Result**: 42 messages sent. 3 book jobs. Friday is full.

## Functional Requirements

### 1. Augmented Audience Segmentation (Unified Search)

- **Requirement**: Leverage "Unified Search" (Spec 005) to interpret natural language queries into database filters.
- **Capabilities**: Filter by Location, Past Services, Customer Tags (e.g., "Converted Once").
- **Output**: A precise list of distinct Customer IDs.

### 2. Multi-Channel Delivery

- **Email**:
  - Integration: SMTP (standard).
  - Config: User provides Host, Port, Username, Password.
  - Content: Rich text (Markdown support or simple HTML).
- **WhatsApp**:
  - Integration: Twilio (via Account SID/Auth Token).
  - Config: User provides Twilio credentials.
  - Content: Text templates (HSM if strict, or freeform if 24h window active).

### 3. Campaign Drafting & AI Refinement

- **Drafting**: User can draft manually or ask AI to "Make this sound more professional" or "Shorten it for WhatsApp".
- **Preview**: Show segment size and message sample.

### 4. Safety & "Blast Protocol"

- **Gate**: Critical stop before sending.
- **Validation**:
  - Show EXACT count of recipients.
  - Show 2-3 sample names.
- **Lock**: Button is disabled until user types a confirmation phrase (e.g., "EXECUTE BLAST").

## Success Criteria

- [ ] User can define a segment via natural language (e.g., "Customers in Cork").
- [ ] System accurately identifies the subset of customers (verified against DB).
- [ ] User can successfully send a test email blast via SMTP.
- [ ] User can successfully send a test WhatsApp blast via Twilio.
- [ ] "Blast Protocol" successfully prevents accidental sends (UI test).

## Technical Considerations

- **Twilio**: Requires handling rate limits and potential error callbacks.
- **SMTP**: Bulk sending might trigger spam filters; suggest batching (e.g., 10 emails/sec).
- **Unified Search**: Ensure Spec 005 can export/return IDs for the segment.

## Assumptions

- Users have their own Twilio/SMTP credentials.
- We rely on Spec 005 for the heavy lifting of NLP -> Query.

## Questions (Resolved)

- **Segmentation**: Using Unified Search.
- **Channels**: SMTP and Twilio.
- **Safety**: "Draft & Review" + Typed Confirmation.
