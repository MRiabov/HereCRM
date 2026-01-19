---
work_package_id: WP04
subtasks:
  - T015
  - T016
  - T017
lane: "doing"
agent: "Antigravity"
history:
  - date: 2026-01-19
    action: created
---

# WP04 - Generic Webhook Integration

## Objective

Create a generic endpoint for external systems to inject messages into the CRM.

## Context

Third-party tools (Zapier, Forms) need a way to create leads or send messages without using a specific channel provider like Twilio.

## Subtasks

### T015: Create Generic Webhook Endpoint

- Create `POST /webhooks/generic`.
- Define JSON Schema:

  ```json
  {
    "identity": "+1234567890", // or email
    "message": "Hello world",
    "source": "Zapier" // optional metadata
  }
  ```

- Implement validation.

### T016: Implement Mapping Logic

- Parse `identity`. Check if it looks like a phone number or email.
- Lookup `User` by that identity.
- Create `Message` entry.

### T017: Test Integration

- Create a simple test script or use `curl` to post data and verify it appears in the system.

## Test Strategy

- **Unit**: Test payload validation logic.
- **Integration**: Post data to the endpoint and check database for new Message.

## Activity Log

- 2026-01-19T18:48:28Z – Antigravity – lane=doing – Started implementation of Generic Webhook
