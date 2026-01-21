---
work_package_id: "WP03"
subtasks:
  - "T010"
  - "T011"
  - "T012"
title: "Ingestion - Messenger Handlers"
phase: "Phase 2 - Messenger Integration"
lane: "doing"
dependencies: ["WP01"]
agent: "Antigravity"
shell_pid: "4059401"
review_status: "has_feedback"
reviewed_by: "MRiabov"
history:
  - timestamp: "2026-01-21T10:21:37Z"
    lane: "planned"
    agent: "antigravity"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 – Ingestion - Messenger Handlers

## Objectives & Success Criteria

- WhatsApp `location` messages are parsed and trigger DB location updates.
- SMS messages containing map links are parsed and trigger DB location updates.
- Employees receive an automatic confirmation when their location is tracked.

## Context & Constraints

- Supporting docs: `kitty-specs/014-live-location-tracking/plan.md`.
- Dependent on: `WP01` (`LocationService`).
- Files involved: `src/services/whatsapp_service.py`, `src/services/twilio_service.py`.

## Subtasks & Detailed Guidance

### Subtask T010 – WhatsApp location message support

- **Purpose**: Catch location sharing from WhatsApp.
- **Steps**:
  1. Identify where messages are processed in `src/services/whatsapp_service.py` (likely `process_incoming_message`).
  2. Add logic to check for message `type == "location"`.
  3. Extract `latitude` and `longitude`.
  4. Call `LocationService.update_location`.
- **Files**: `src/services/whatsapp_service.py`

### Subtask T011 – Twilio location link support

- **Purpose**: Fallback for SMS users.
- **Steps**:
  1. Modify `src/services/twilio_service.py` to intercept incoming text.
  2. If the message isn't a recognized command, call `LocationService.parse_location_from_text`.
  3. If coordinates are found, update user location.
- **Files**: `src/services/twilio_service.py`

### Subtask T012 – Auto-reply acknowledgment

- **Purpose**: Give feedback to the employee.
- **Steps**:
  1. Upon successful location update via either channel, send a reply: "Thanks, your location has been updated and tracking is active."
  2. Ensure this doesn't create a loop of messages.
- **Files**: `src/services/whatsapp_service.py`, `src/services/twilio_service.py`

## Definition of Done Checklist

- [ ] Sending a location attachment on WhatsApp updates the user in DB.
- [ ] Sending a Google Maps link via SMS updates the user in DB.
- [ ] Confirmation message is received by the sender.
- [ ] `tasks.md` updated with status change.

## Review Guidance

- Test that sending a normal text message doesn't trigger the location logic unless it really looks like a map link.
- Ensure the user ID is correctly identified from the sender's phone number.

## Activity Log

- 2026-01-21T10:21:37Z – antigravity – lane=planned – Prompt created.
- 2026-01-21T10:45:08Z – unknown – lane=for_review – Ready for review: Implemented Autoroute Command Preview (read-only mode) with data fetching, routing service integration, and human-readable preview display.
- 2026-01-21T10:45:39Z – Antigravity – shell_pid=4035720 – lane=doing – Started review via workflow command
- 2026-01-21T10:48:06Z – Antigravity – shell_pid=4035720 – lane=planned – Moved to planned
- 2026-01-21T11:39:26Z – Antigravity – shell_pid=4059401 – lane=doing – Started implementation via workflow command
