---
work_package_id: WP04
subtasks:
  - T014
  - T015
  - T016
  - T017
  - T018
lane: "done"
review_status: "approved without changes"
reviewed_by: Antigravity
agent: "claude"
shell_pid: "0"
assignee: "Antigravity"
history:
  - date: 2026-01-17
    action: created
    agent: Antigravity
  - date: 2026-01-18
    action: approved
    agent: Antigravity
    note: "WhatsApp state handlers and exit paths verified."
---

# Work Package 04: WhatsApp Interface Integration

## Objective

Expose the import/export functionality via a dedicated "Data Management" conversation state.

## Context

The user interface is entirely within WhatsApp. We need a new state `DATA_MANAGEMENT` to sequester these operations.

## Subtasks

### T014: Update ConversationStatus

- **File**: `src/uimodels.py` (or where `ConversationStatus` is defined).
- **Action**: Add `DATA_MANAGEMENT` to the Enum.

### T015: State Transitions

- **File**: `src/services/whatsapp_service.py`
- **Action**:
  - In `MAIN_MENU` or global handler, listen for "manage data" or similar command.
  - Transition `user.state` -> `DATA_MANAGEMENT`.
  - Send welcome message: "You are in Data Management mode. Send a file to import, or say 'Export...' to download data."

### T016: Handle File Uploads

- **Action**: In `handle_data_management_state`:
  - Detect if message has media (document/MIME type).
  - If yes:
    - Download media (using Twilio/WhatsApp API helper).
    - Create `ImportJob(status=PENDING)`.
    - Trigger async processing (via background task or queue).
    - Reply: "Import started. You will be notified when done."

### T017: Handle Text Commands

- **Action**: In `handle_data_management_state`:
  - If text starts with "Export":
    - Create `ExportRequest(status=PENDING)`.
    - Trigger async processing.
    - Reply: "Generating export..."
  - If text is "Exit":
    - Transition -> `MAIN_MENU`.
    - Reply: "Returned to main menu."

### T018: Testing

- **Action**: Create `tests/test_data_management_flow.py`.
- **Cases**:
  - Enter state.
  - Send file -> Mock import job creation.
  - Send export command -> Mock export request.
  - Exit state.

## Definition of Done

- Start-to-finish flow works via WhatsApp simulator/tests.
- Users can switch into and out of Data Management mode.
- File uploads trigger imports.

## Risks

- User navigation confusion: Make sure "Exit" is always available and advertised.

## Activity Log

- 2026-01-17T21:05:22Z – antigravity – shell_pid= – lane=for_review – Already implemented and verified by tests.
- 2026-01-18T07:10:23Z – claude – shell_pid=0 – lane=done – Final acceptance
