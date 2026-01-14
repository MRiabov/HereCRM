---
work_package_id: "WP02"
subtasks:
  - "T006"
  - "T007"
  - "T008"
  - "T009"
title: "Service Catalog Management"
phase: "Phase 2 - Feature Development"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-14T19:10:01Z"
    lane: "planned"
    agent: "antigravity"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 – Service Catalog Management

## Objectives & Success Criteria

- Implement a "Settings" mode in the WhatsApp chat bot.
- Allow admin users to perform CRUD operations on the `Service` catalog.
- Ensure the catalog management is isolated from regular job creation workflows to prevent accidents.

## Context & Constraints

- Users enter "Settings" by typing a specific command (e.g., "Settings").
- In this state, the LLM or state machine should handle service management.
- Refer to `spec.md` for acceptance scenarios of service management.

## Subtasks & Detailed Guidance

### Subtask T006 – Add Settings message templates

- **Purpose**: Define user feedback messages for settings workflows.
- **Steps**:
  - Update `src/assets/messages.yaml` with keys for settings menu, service added, service deleted, etc.
- **Files**: `src/assets/messages.yaml`
- **Parallel?**: Yes

### Subtask T007 – Implement `SETTINGS` state

- **Purpose**: Manage the user session state.
- **Steps**:
  - Add `SETTINGS` to the `ChatState` (or equivalent) in `whatsapp_service.py`.
  - Implement entry/exit logic for the settings state.
- **Files**: `src/services/whatsapp_service.py`
- **Parallel?**: No

### Subtask T008 – Implement CRUD for `Service`

- **Purpose**: Provide the business logic for managing services.
- **Steps**:
  - Handle commands like "Add Service [Name] [Price]", "List Services", "Delete Service [ID/Name]".
  - Call `ServiceRepository` to persist changes.
- **Files**: `src/services/whatsapp_service.py`
- **Parallel?**: No

### Subtask T009 – Create `chat_utils.py`

- **Purpose**: Helper for formatting list/tables in chat.
- **Steps**:
  - Implement a utility function to format lists of items (like services) as readable text tables.
- **Files**: `src/services/chat_utils.py`
- **Parallel?**: Yes

## Risks & Mitigations

- Accidental state stickiness: Ensure users can easily exit the settings menu.
- Unauthorized access: Currently simple, but consider if only certain phone numbers can access settings.

## Definition of Done Checklist

- [ ] All subtasks completed and validated
- [ ] Users can enter settings, add a service, and see it in the list
- [ ] Exit command works as expected
- [ ] Messages match templates in `messages.yaml`

## Activity Log

- 2026-01-14T19:10:01Z – antigravity – lane=planned – Prompt generated via /spec-kitty.tasks
