---
work_package_id: "WP04"
subtasks:
  - "T011"
  - "T012"
title: "Conversational UX & Prompts"
phase: "Phase 4 - Conversational Polish"
lane: "planned"
dependencies: ["WP01", "WP03"]
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-22T08:25:20Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 – Conversational UX & Prompts

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

- Dynamically trigger system prompts for invoices/quotes when settings are "Automatic".
- Refine the Assistant's core behavior to honor business-specific "invisibility" (e.g., don't mention invoices if the business never sends them).

### Success Criteria

- [ ] System generates prompts for invoicing/quoting ONLY when business setting is `automatic`.
- [ ] Global system instruction is updated to guide Assistant behavior regarding workflow state.
- [ ] Assistant conceptual filtering works (doesn't offer disabled tools in conversational context).

## Context & Constraints

- Follows behavior defined in `spec.md` Section 2.4.4.
- Uses `messages.yaml` for template-based system messages.

## Subtasks & Detailed Guidance

### Subtask T011 – Update `assets/messages.yaml` with conditional prompts

- **Purpose**: Automate workflow suggestions.
- **Steps**:
    1. Update/Add templates for:
        - `suggest_invoice`: Triggered when job is completed and `workflow_invoicing == 'automatic'`.
        - `suggest_quote`: Triggered when lead is added and `workflow_quoting == 'automatic'`.
    2. Add conditional help text for various system states that mentions workflow benefits.
- **Files**: `assets/messages.yaml`

### Subtask T012 – Update global system instruction

- **Purpose**: Direct Assistant mental model for workflow sensitivity.
- **Steps**:
    1. Update the Assistant's system prompt (usually in a config or code file that defines the LLM context).
    2. Add instruction: "Adapt to the business workflow settings provided in the context. If a feature (Invoicing, Quoting, etc.) is disabled ('never'), do not mention it, offer it, or prompt for it. Treat it as if the capability does not exist in the system for this business."
- **Files**: `src/config.py` (or wherever system instructions are injected)

## Test Strategy

- **Manual Test**: Simulate completion of a job for a business with `workflow_invoicing = 'automatic'` and verify the system suggests sending an invoice.
- **Manual Test**: As a business with `workflow_invoicing = 'never'`, ask the agent "What features do you have?". Verify it doesn't mention invoicing.

## Definition of Done Checklist

- [ ] All subtasks completed and validated
- [ ] System prompts behave as expected
- [ ] `tasks.md` updated with status change

## Activity Log

- 2026-01-22T08:25:20Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
