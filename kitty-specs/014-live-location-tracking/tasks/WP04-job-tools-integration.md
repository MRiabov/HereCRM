---
work_package_id: WP04
title: Implementation - Tools & Integration
lane: planned
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
