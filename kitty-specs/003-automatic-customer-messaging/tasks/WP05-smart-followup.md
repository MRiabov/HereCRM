---
work_package_id: WP05
subtasks:
  - T014
  - T015
  - T016
  - T017
lane: "planned"
---

# Work Package 05: Smart Follow-up Engine

## Goal

Automate the process of following up on unconverted quotes using AI to draft personalized messages for owner approval.

## Context

Businesses lose significant revenue from quotes that are sent but not acted upon. An automated "nag" engine reduces manual overhead.

## Subtasks

### T014: Implement Quote Sent reminder logic (48h delay)

- **Backend**: Track when a quote enters `SENT` status.
- **Timer**: Create a background task or scheduled check that identifies quotes in `SENT` status for > 48 hours (configurable).
- **Trigger**: Emit a `QuoteReminderEvent` when the criteria are met.

### T015: Integrate LLM for personalized follow-up drafting

- **Service**: In the `MessagingService` (or a specific `FollowUpService`), call the LLM to generate a follow-up draft.
- **Context**: Pass the quote details (items, value, customer name, original message date) to the LLM.
- **Prompt**: "Draft a friendly, professional follow-up for this quote: [Details]. Keep it short."

### T016: Implement approval flow for follow-ups

- **Workflow**: Instead of sending automatically, save the draft to a `MessageLog` or a new `FollowUpDraft` table.
- **Interaction**: Notify the business owner (e.g., via chat: "AI drafted a follow-up for [Customer]. Send it? [Draft Content]").
- **Approval**: Add a tool/command for the owner to `ApproveFollowUp` or `EditFollowUp`.

### T017: Add configuration settings for follow-ups

- **Settings**: Add `followup_enabled` (bool) and `followup_delay_hours` (int) to the system/user settings.
- **Validation**: Ensure the logic respects these settings.

## Verification

- Create a quote and mark as `SENT`.
- Mock time to passage of 48 hours.
- Verify that a draft is generated and the owner is notified.
- Approve the draft and verify it is sent to the customer.

## Activity Log
