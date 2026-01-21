---
work_package_id: "WP05"
subtasks:
  - "T020"
  - "T021"
  - "T022"
  - "T023"
title: "Request to Quote Promotion"
phase: "Phase 3 - Conversational Workflows"
lane: "doing"
assignee: ""
agent: "Antigravity"
shell_pid: "4007482"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-21T09:50:41Z"
    lane: "planned"
    agent: "Antigravity"
    shell_pid: ""
    action: "Prompt generated to fulfill user request for implementation"
---

# Work Package Prompt: WP05 – Request to Quote Promotion

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately (right below this notice).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review. If you see feedback here, treat each item as a must-do before completion.]*

---

## Objectives & Success Criteria

- Enable promoting an existing customer request to a formal Quote.
- "Promote request" action successfully creates a Quote populated with request details.
- Success criteria: Quote is created, linked to request, and sent to customer if requested.

## Context & Constraints

- Dependent on WP01 (Models), WP02 (PDF/Sending), and WP03 (LLM Tools).
- Similar to "Request -> Job" promotion logic.
- Reference `kitty-specs/012-conversational-quotations/spec.md` (FR-009).

## Subtasks & Detailed Guidance

### Subtask T020 – Implement QuoteService.create_from_request logic

- **Purpose**: Core logic for converting a Request entity into a Quote.
- **Steps**:
  1. Edit `src/services/quote_service.py`.
  2. Implement `create_from_request(request_id: int, items: List[QuoteLineItemInput] = None) -> Quote`:
     - Fetch the `Request`.
     - Create a `Quote` using the `Request`'s customer data and description.
     - If `items` are provided, use them for the QuoteLineItems.
     - Move Request to a 'promoted' or 'resolved' state if appropriate (check existing conventions for Request -> Job).
- **Files**: `src/services/quote_service.py`

### Subtask T021 – Add "Promote to Quote" action to ConvertRequestTool

- **Purpose**: Allow the LLM to choose "Quote" as a promotion target.
- **Steps**:
  1. Edit `src/uimodels.py`.
  2. Update `ConvertRequestTool.action` description to include 'quote'.
  3. Edit `src/tool_executor.py`.
  4. In `execute_tool`'s `ConvertRequestTool` handling, if action is 'quote', call `QuoteService.create_from_request`.
- **Files**: `src/uimodels.py`, `src/tool_executor.py`

### Subtask T022 – Update WhatsAppService to handle "Promote to Quote" flow

- **Purpose**: Interface for the promotion flow in WhatsApp.
- **Steps**:
  1. Usually handled via `ToolExecutor` and `LLMParser` automatically, but ensure the prompt/instructions in `prompts.yaml` are updated if needed.
  2. Verify if any special handling in `src/services/whatsapp_service.py` is needed for the confirmation message after promotion.
- **Files**: `src/assets/prompts.yaml`, `src/services/whatsapp_service.py`

### Subtask T023 – Write tests for Request -> Quote promotion

- **Purpose**: Verify the promotion flow.
- **Steps**:
  1. Create `tests/integration/test_request_promotion.py`.
  2. Test scenarios: Promote a request with items, promote without items (draft quote).
  3. Verify Quote is correctly linked/populated.
- **Files**: `tests/integration/test_request_promotion.py`

## Activity Log

- 2026-01-21T09:50:41Z – Antigravity – lane=planned – Prompt created.
- 2026-01-21T09:52:45Z – Antigravity – shell_pid=4007482 – lane=doing – Started implementation via workflow command
