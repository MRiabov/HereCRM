# Implementation Plan: [FEATURE]

*Path: [templates/plan-template.md](templates/plan-template.md)*

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]
**Input**: Feature specification from `/kitty-specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/spec-kitty.plan` command. See `.kittify/templates/commands/plan.md` for the execution workflow.

The planner will not begin until all planning questions have been answered—capture those answers in this document before progressing to later phases.

## Summary

[Extract from feature spec: primary requirement + technical approach from research]

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: [e.g., Python 3.11, Swift 5.9, Rust 1.75 or NEEDS CLARIFICATION]  
> **State the core technical decisions for this feature.**

- **Scheduler Strategy**: We will use `APScheduler` (packaged as `src/services/scheduler.py`) running within the main FastAPI application to handle the "Shift Starter" events (6:30 AM employee local time). This avoids setting up external infrastructure like Celery/Redis for this MVP.
- **Job Completion**: We will implement a new LLM tool `CompleteJobTool` (triggered by "done #123") that updates the job status and triggers the "Next Job Guide" logic.
- **Service Reminders**: We will extend the `Service` entity (and `ServiceRepository`) to include a `reminder_text` field. We will update the `EditServiceTool` to allow business owners to configure this field (e.g., "Set reminder for Window Cleaning to 'Ask about interiors'").
- **State Management**: The "Guided Workflow" is state-dependent. We will rely on the `Job` status ("scheduled" -> "in_progress" -> "completed") and the `User` (employee) context to determine the "next job".
- **Employee Management Context**: We will implement an `EmployeeManagementTool` that shifts the conversation context to a "Settings" mode (similar to Workflow Settings in Spec 019). This tool will list current employees and surface management-specific tools.
- **Invitation Flow**: Restricted to the Management Context. We will introduce an `Invitation` entity. A `InviteUserTool` will allow owners to send invites. A `JoinBusinessTool` (keyword responder) will handle-acceptance.
- **Role Management & Dismissal**: Restricted to the Management Context. `PromoteUserTool` for role upgrades and `DismissUserTool` (Forceful Departure) to remove employees from the business.
- **Messaging**: Leveraging the existing `MessagingService` (WhatsApp/Twilio) to send the push notifications.

## Constitution Check

> **Does this feature align with the project constitution?**

- [x] **Agentic**: Uses LLMs for "done" commands and natural language parsing.
- [x] **Text-First**: All interactions (warnings, schedules, completions) happen via chat.
- [x] **Simplicity**: No new apps or complex dashboards for the employee; just text.

*Constitution check passed.*

## Gateways

- [x] **UX Strategy confirmed?** (Yes, text-based guided flow)
- [x] **Database changes understood?** (Yes, `Service` model update, potential `User` timezone field)
- [x] **Dependent features ready?** (Yes, Employee Management Dashboard is the foundation)

---

## Phase 0: Research (Validation)

**Goal**: Ensure we have the right libraries and patterns before coding.

- [ ] **Research Task 1**: Best practices for `APScheduler` with `asyncio` in FastAPI to ensuring it doesn't block the main loop.
- [ ] **Research Task 2**: Verify how to access "Employee Local Time". Do `User` entities currently store a timezone? If not, we might need to add it or default to the Business timezone.
- [ ] **Research Task 3**: Check `MessagingService` capabilities for proactive outbound messages (initiating a conversation flow vs replying).

## Phase 1: Design & Contracts

**Goal**: Define the schema and tools.

- [ ] **Data Model (`data-model.md`)**:
  - Add `reminder_text` (Text, nullable) to `Service` model.
  - Check/Add `timezone` to `User` or `Business`.
  - Add `role` (String, default='employee') to `User` model.
  - [NEW] Add `Invitation` entity (inviter_id, invitee_identifier, business_id, status, token).
- [ ] **Contracts (`contracts/`)**:
  - **Tools**: Define `CompleteJobTool` schema.
  - **Tools**: Update `AddServiceTool` / `EditServiceTool` schemas to include `reminder_text`.
  - **Tools**: Define `EmployeeManagementTool` (for entering the management context).
  - **Tools**: Define `InviteUserTool`, `JoinBusinessTool`, `PromoteUserTool`, `DismissUserTool`.
  - **Events**: Define `SHIFT_STARTED` event payload.
- [ ] **Agent Context**: Update `system_prompt` to understand the Employee Management context and restrict tools appropriately.

## Project Structure

### Documentation (this feature)

```
kitty-specs/[###-feature]/
├── plan.md              # This file (/spec-kitty.plan command output)
├── research.md          # Phase 0 output (/spec-kitty.plan command)
├── data-model.md        # Phase 1 output (/spec-kitty.plan command)
├── quickstart.md        # Phase 1 output (/spec-kitty.plan command)
├── contracts/           # Phase 1 output (/spec-kitty.plan command)
└── tasks.md             # Phase 2 output (/spec-kitty.tasks command - NOT created by /spec-kitty.plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```
# [REMOVE IF UNUSED] Option 1: Single project (DEFAULT)
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/

# [REMOVE IF UNUSED] Option 2: Web application (when "frontend" + "backend" detected)
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# [REMOVE IF UNUSED] Option 3: Mobile + API (when "iOS/Android" detected)
api/
└── [same as backend above]

ios/ or android/
└── [platform-specific structure: feature modules, UI flows, platform tests]
```

**Structure Decision**: [Document the selected structure and reference the real
directories captured above]

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
