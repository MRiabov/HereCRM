---
work_package_id: WP03
subtasks:
  - T010
  - T011
  - T012
  - T013
lane: "for_review"
agent: "codex"
history:
  - date: 2026-01-13
    status: planned
    agent: spec-kitty
---
# Work Package: Core CRM Logic & State Machine

## Objective

Build the application's "brain" that orchestrates the flow between receiving a message, maintaining conversation state, handling multi-turn confirmation dialogues, and executing the final database operations.

## Context

Messages cannot just be executed immediately. We need a State Machine (IDLE -> WAITING_CONFIRM). We also need "Drafts" to store what the user *wants* to do until they say "Yes". Undo functionality requires transactional awareness.

## Subtasks

### T010: WhatsappService Skeleton

- Create `src/services/whatsapp_service.py`.
- Define `handle_message(business_id, user_phone, message_text)`.
- Dependency injection: Needs access to `ConversationStateRepository` and `LLMParser`.

### T011: Confirmation Flow

- Implement logic in `handle_message`:
  - Fetch `ConversationState` for user.
  - If state is `WAITING_CONFIRM`:
    - Check if message is "Yes"/"Confirm" or "No"/"Cancel".
    - If "Yes": Execute the draft action (stored in JSON).
    - If "No": Discard draft, reset state to `IDLE`.
    - **Edge Case**: If message is neither (e.g., a new command):
      - Load user preference `confirm_by_default` (default: False).
      - If `True`: Auto-execute draft, then process new message.
      - If `False` (default): Discard draft (Undo), notify "Draft discarded", then process new message.
  - If state is `IDLE`:
    - Parse message with `LLMParser`.
    - If valid tool call:
      - Save tool call to `draft_data`.
      - Set state to `WAITING_CONFIRM`.
      - Return "Please confirm: [Summary]" message.

### T012: Undo Logic

- To implement "Undo", we need to track the `last_operation_id` or similar.
- Strategy: Store the inverse action or simply the ID of the created record in `ConversationState` (new field `last_modified_entity`).
- On "Undo":
  - Check `last_modified_entity` (e.g., `Job:123`).
  - Delete that entity.
  - Clear the field.
  - Return "Undone".

  - Return "Undone".
  
### T013a: Request Conversion Logic

- Implement logic to "promote" a Request to a Job.
- Input: `query` (fuzzy match against Request content or linked User/Phone).
- Action:
  1. Find target `Request`.
  2. Create new `Job` copying content.
  3. Apply `action` (e.g. set status=COMPLETED or update schedule if `time` provided).
  4. **Delete** original `Request`.
  5. Return "Converted Request to Job: [Details]".

### T013: Tool Executor

- Create `src/tool_executor.py`.
- Maps `AddJobTool` -> `JobRepository.create()`.
- Maps `ScheduleJobTool` -> `JobRepository.update()`.
- Maps `UpdateSettingsTool` -> `UserRepository.update_preferences()`.
- Maps `ConvertRequestTool` -> `Service.convert_request()`.
- Ensure all DB calls pass the `business_id` from the context.

## Definition of Done

- [ ] State Machine works: Command -> "Confirm?" -> "Yes" -> Saved.
- [ ] Drafts are correctly serialized/deserialized from DB.
- [ ] Undo works for the most recent creation action.
- [ ] Unit/Integration tests cover the state transitions.

## Activity Log

- 2026-01-13T11:55:14Z – codex – lane=doing – Started implementation
- 2026-01-13T12:01:52Z – codex – lane=for_review – Ready for review
