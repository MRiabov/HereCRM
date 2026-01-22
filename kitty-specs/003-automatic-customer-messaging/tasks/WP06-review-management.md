---
work_package_id: WP06
subtasks:
  - T018
  - T019
  - T020
lane: "planned"
---

# Work Package 06: Review & Reputation Management

## Goal

Automatically request reviews from customers after a job has been paid, improving local SEO and reputation.

## Context

Reviews are critical for local business growth. Automating the request immediately after a successful transaction (payment) maximizes conversion.

## Subtasks

### T018: Implement Job Paid review request logic (2h delay)

- **Event**: Subscribe to `JOB_PAID` event.
- **Timer**: Schedule a message to be sent 2 hours after the event (configurable).
- **Logic**: Ensure the job remains in a "completed" or "paid" state and no previous review request was sent for this job.

### T019: Create review request template with configurable links

- **Template**: "Hi [Name], thanks for choosing us! If you're happy with the work, would you mind leaving us a quick review? [Link]"
- **Dynamic Content**: Inject customer name and the configured review link.

### T020: Add configuration settings for review requests

- **Settings**:
  - `review_requests_enabled` (bool)
  - `review_request_delay_hours` (int, default 2)
  - `review_link_google` (string)
  - `review_link_yelp` (string)
- **Persistence**: Ensure these are stored and accessible by the `MessagingService`.

## Verification

- Mark a job as `PAID`.
- Wait (or mock) 2 hours.
- Verify the review request message is sent to the customer with the correct link.
- Disable settings and verify no message is sent.

## Activity Log
