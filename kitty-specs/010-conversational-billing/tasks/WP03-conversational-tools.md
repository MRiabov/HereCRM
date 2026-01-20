---
work_package_id: "WP03"
subtasks:
  - "T013"
  - "T014"
  - "T015"
  - "T016"
title: "Conversational Tools & State Transitions"
phase: "Phase 4 - User Interface"
lane: "doing"
dependencies: ["WP01"]
agent: "Antigravity"
shell_pid: "3837511"
history:
  - timestamp: "2026-01-20T14:45:30Z"
    lane: "planned"
    agent: "antigravity"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 – Conversational Tools & State Transitions

## Objectives & Success Criteria

- Expose billing functionality to the user via LLM tools.
- Enable smooth transitions into the `BILLING` state.
- Provide clear, template-driven messaging for billing inquiries.

## Context & Constraints

- Integrates with the existing `ToolExecutor` and `llm_client.py`.
- Uses message templates from `src/assets/messages.yaml`.

## Subtasks & Detailed Guidance

### Subtask T013 – Define billing tools

- **Purpose**: Create Pydantic schemas for LLM to call.
- **Steps**:
  1. Add `GetBillingStatusTool` (no args).
  2. Add `RequestUpgradeTool` (args: `item_name`, `quantity`?).
  3. Define these in `src/uimodels.py`.
- **Files**: `src/uimodels.py`

### Subtask T014 – Hook tools into executor

- **Purpose**: Map tool calls to service methods.
- **Steps**:
  1. Update `src/tool_executor.py` to handle `GetBillingStatusTool` and `RequestUpgradeTool`.
  2. Inject `BillingService` and call its methods.
- **Files**: `src/tool_executor.py`

### Subtask T015 – Implement state transition logic

- **Purpose**: Ensure user moves to `BILLING` state when appropriate.
- **Steps**:
  1. Update `WhatsappService.handle_message` (or equivalent state machine logic) to recognize billing-related intent.
  2. Transition user's `ConversationState` to `BILLING` when they ask for billing info.
- **Files**: `src/services/whatsapp_service.py` (or relevant state handler)

### Subtask T016 – Create message templates

- **Purpose**: Professionalize the conversational output.
- **Steps**:
  1. Add `billing_status`, `billing_upgrade_quote`, and `payment_link_ready` templates to `src/assets/messages.yaml`.
  2. Ensure variables like `plan`, `seats`, `addons`, and `url` are supported.
- **Files**: `src/assets/messages.yaml`

## Risks & Mitigations

- **LLM Hallucination**: Ensure tools have clear docstrings so the LLM knows when to call them.
- **State Stuck**: Ensure there is a way to exit the `BILLING` state (e.g., "back" or timeout).

## Definition of Done Checklist

- [ ] `GetBillingStatusTool` and `RequestUpgradeTool` registered and working
- [ ] User state updates to `BILLING` on request
- [ ] Messages rendered via templates
- [ ] E2E tests for "billing" command show correct status

## Review Guidance

- Verify that the `RequestUpgradeTool` correctly handles ambiguous requests by asking clarifying questions (via LLM).
- Check the wording of message templates for professional tone.

## Activity Log

- 2026-01-20T14:45:30Z – antigravity – lane=planned – Prompt created.
- 2026-01-20T16:52:19Z – Antigravity – shell_pid=3837511 – lane=doing – Started implementation via workflow command
