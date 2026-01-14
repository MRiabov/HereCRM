---
work_package_id: "WP04"
subtasks:
  - "T014"
  - "T015"
title: "UI & Reporting"
phase: "Phase 3 - Polish & Launch"
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

# Work Package Prompt: WP04 – UI & Reporting

## Objectives & Success Criteria

- Provide visual feedback to users about the line items added to jobs.
- Display a detailed breakdown when showing job details.
- Achievement: "Show Job" command outputs a table of line items with totals.

## Context & Constraints

- WhatsApp has limited formatting (fixed-width via backticks).
- Summaries should be concise but informative.

## Subtasks & Detailed Guidance

### Subtask T014 – Update "Show Job" output

- **Purpose**: Display line items in a table-like format.
- **Steps**:
  - Update the job details renderer (likely in `whatsapp_service.py` or a message template).
  - Format line items as: `Service Name | Qty | Price | Total`.
- **Files**: `src/services/whatsapp_service.py`, `src/assets/messages.yaml`
- **Parallel?**: Yes

### Subtask T015 – Update confirmation messages

- **Purpose**: Show a summary of inferred items immediately after creation.
- **Steps**:
  - Update the `add_job` confirmation template to include a short list of line items.
- **Files**: `src/assets/messages.yaml`
- **Parallel?**: Yes

## Risks & Mitigations

- Message length: Multiple line items could make the message very long; consider truncation if the list exceeds 5-10 items.

## Definition of Done Checklist

- [ ] "Show Job" displays line items correctly
- [ ] Confirmation messages include line item summaries
- [ ] Formatting is readable on mobile (WhatsApp)

## Activity Log

- 2026-01-14T19:10:01Z – antigravity – lane=planned – Prompt generated via /spec-kitty.tasks
