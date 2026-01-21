---
work_package_id: WP04
title: Implementation - Tools & Integration
lane: "done"
dependencies:
- WP01
- WP02
subtasks:
- T013
- T014
- T015
- T016
- T017
phase: Phase 3 - User Facing Features
agent: "Antigravity"
shell_pid: "4074088"
reviewed_by: "MRiabov"
review_status: "has_feedback"
history:
- timestamp: '2026-01-21T10:21:37Z'
  lane: planned
  agent: antigravity
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP04 – Implementation - Tools & Integration

## Objectives & Success Criteria

- Automated ETA responses for customers asking about arrival time.
- Admin tool to locate specific employees.
- End-to-end integration test validating the "Where is my technician?" flow.

## Context & Constraints

- Supporting docs: `kitty-specs/014-live-location-tracking/spec.md`, `plan.md`.
- Tool registration: `src/services/inference_service.py` and `src/services/tool_executor.py`.
- Logical dependency: Finding the *active job* is critical to identifying which employee to track for a customer.

## Subtasks & Detailed Guidance

### Subtask T013 – Active job lookup logic

- **Purpose**: Link a customer to the correct technician.
- **Steps**:
  1. Implement `JobService.get_active_job_for_customer(phone_number: str)`.
  2. Logic: Search for jobs where `customer_phone == phone_number`.
  3. Filter by time: `start_time - 30m <= now <= end_time + 30m`.
  4. Return the first matching job or None.
- **Files**: `src/services/crm_service.py` (or dedicated job service if exists).

### Subtask T014 – LocateEmployeeTool (Admin)

- **Purpose**: Allow dispatchers to see where staff are.
- **Steps**:
  1. Create `LocateEmployeeTool` class in `src/services/tool_executor.py`.
  2. Params: `employee_name` (optional).
  3. Returns: A message with the address (if geocodable from lat/lng) or a Google Maps link and "last updated" timestamp.
- **Files**: `src/services/tool_executor.py`

### Subtask T015 – CheckETATool (Customer)

- **Purpose**: Power the arrival estimate feature.
- **Steps**:
  1. Create `CheckETATool`.
  2. Internal Logic:
     - Find sender's active job (T013).
     - Identify assigned technician.
     - Get technician's latest location.
     - If location >30m stale, return "Technician is en route, contact office for details".
     - Calculate ETA via `RoutingService.get_eta_minutes`.
     - Return "We are approximately [X] minutes away."
- **Files**: `src/services/tool_executor.py`

### Subtask T016 – Tool Registration & Prompting

- **Purpose**: Expose tools to the LLM.
- **Steps**:
  1. Register `LocateEmployeeTool` and `CheckETATool` in `src/services/tool_executor.py`.
  2. Update `src/services/inference_service.py` system prompts/tool definitions to explain when to use these tools.
- **Files**: `src/services/inference_service.py`, `src/services/tool_executor.py`

### Subtask T017 – End-to-End Integration Test

- **Purpose**: Final verification.
- **Steps**:
  1. Create `tests/integration/test_location_eta_flow.py`.
  2. Setup: Mock job, mock technician location.
  3. Simulate customer asking "Where is the tech?".
  4. Assert response contains the correct rounded ETA.
- **Files**: `tests/integration/test_location_eta_flow.py`

## Definition of Done Checklist

- [ ] `CheckETATool` accurately calculates arrival time.
- [ ] `LocateEmployeeTool` provides links for staff locations.
- [ ] LLM correctly triggers tools for location-related queries.
- [ ] Integration test passes.
- [ ] `tasks.md` updated with status change.

## Review Guidance

- Ensure `LocateEmployeeTool` is restricted to Admin/Owner roles if possible (or check business context).
- Check the time window logic for "active jobs" to ensure it covers common early/late scenarios.

## Activity Log

- 2026-01-21T10:21:37Z – antigravity – lane=planned – Prompt created.
- 2026-01-21T12:04:49Z – Antigravity – shell_pid=4070339 – lane=doing – Started implementation via workflow command
- 2026-01-21T12:21:28Z – Antigravity – shell_pid=4070339 – lane=for_review – Ready for review: Implemented LocateEmployeeTool and CheckETATool, added get_active_job_for_customer to CRMService, and extended OpenRouteServiceAdapter with ETA calculation. Integration tests verified.
- 2026-01-21T12:27:09Z – Antigravity – shell_pid=4073129 – lane=doing – Started review via workflow command
- 2026-01-21T13:03:57Z – Antigravity – shell_pid=4073129 – lane=done – Review passed: Implemented LocateEmployeeTool and CheckETATool with active job lookup, stale location handling, and ORS ETA calculation. Verified with end-to-end integration test.
- 2026-01-21T13:13:56Z – Antigravity – shell_pid=4073129 – lane=doing – Started review via workflow command
- 2026-01-21T13:42:32Z – Antigravity – shell_pid=4073129 – lane=planned – Moved to planned
- 2026-01-21T15:10:20Z – Antigravity – shell_pid=4073129 – lane=doing – Started implementation via workflow command
- 2026-01-21T15:27:19Z – Antigravity – shell_pid=4073129 – lane=for_review – Addressed review feedback: updated system prompts in prompts.yaml, added owner-only check for customer_query in CheckETATool, and refactored routing service to use a provider pattern in ToolExecutor. Verified with integration tests.
- 2026-01-21T15:34:49Z – Antigravity – shell_pid=4074088 – lane=doing – Started review via workflow command
- 2026-01-21T15:36:12Z – Antigravity – shell_pid=4074088 – lane=done – Review passed: Verified integration of routing service, owner role check in CheckETATool, system prompts update, and passing integration tests.
