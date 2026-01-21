---
work_package_id: "WP03"
title: "Autoroute Command - Preview"
lane: "for_review"
dependencies: ["WP02"]
subtasks:
  - "T010"
  - "T011"
  - "T012"
  - "T013"
agent: "Antigravity"
shell_pid: "4007482"
---

# Work Package 03: Autoroute Command - Preview

## Objective

Implement the `autoroute` tool (read-only mode) that fetches data, runs the routing algorithm, and presents a preview of the schedule to the user.

## Context

This is the user-facing entry point. It must gather all necessary context (availability, jobs) and orchestrate the routing service.

## Subtasks

### T010: Scaffold `AutorouteTool`

**Purpose**: Create the tool wrapper and register it.
**Files**: `src/tools/routing_tools.py`, `src/tool_executor.py`, `src/llm_client.py`
**Steps**:

1. Create `src/tools/routing_tools.py`.
2. Define `AutorouteInput` schema (pydantic):
    - `date`: Optional[str] (YYYY-MM-DD), default to today.
3. Define `AutorouteTool` class.
    - `run(self, input: AutorouteInput) -> str`.
4. Register tool in `src/llm_client.py` (model map) and `src/tool_executor.py` (execution logic).

### T011: Implement data fetching

**Purpose**: Gather the state of the world to pass to the Routing Service.
**Files**: `src/tools/routing_tools.py`
**Steps**:

1. In `AutorouteTool.run`:
    - Parse `date`.
    - Fetch `employees` (Users) - filter by active/role if needed (Plan says "Available employees").
    - Fetch `unassigned_jobs` for the date (or backlog).
    - Fetch `CustomerAvailability` for relevant customers.
2. Use existing Services (`UserService`, `JobService`) or use Repositories directly if services miss methods.

### T012: Integrate `RoutingService` execution

**Purpose**: Call the service created in WP02.
**Files**: `src/tools/routing_tools.py`
**Steps**:

1. Instantiate `RoutingServiceProvider` (use factory or dependency injection to genericize ORS vs Mock). *Default to ORS unless configured otherwise.*
2. Call `calculate_routes(jobs, employees, availability)`.
3. Handle `RoutingException` and return user-friendly error.

### T013: Implement Preview display

**Purpose**: Format the `RoutingSolution` into a readable text summary.
**Files**: `src/tools/routing_tools.py`, `src/templates/` (optional)
**Steps**:

1. Format output string:
    - Summary: "Proposed Schedule for [Date]"
    - Metrics: "Total Distance: X km, Est. Time: Y hrs"
    - Per Employee:
        - "Employee A: [Job1 (9:00-10:00)] -> [Job2 (10:30-11:30)]"
    - Unassigned List.
2. Store the `RoutingSolution` in a temporary state (cache/session) if possible, OR just re-calculate on confirmation (simplest for stateless LLM tools). *Decision: Stateless. Re-calculate on confirm or pass a "proposal_id" if we persist proposals. For MVP, re-calculation or stateless verification is safer.*
    - *Correction*: If we re-calculate, it might change. Ideally, we save a "Draft Schedule" to DB or return a unique ID.
    - *Better approach for MVP*: The "Preview" just shows it. The "Confirm" step might accept the *same* input (date) and just apply it, trusting it will be similar, OR the user says "Yes, apply it".
    - *Let's assume*: The tool returns the preview. The User must then say "Confirm". The "Confirm" tool might be a separate call.

## Test Strategy

- **Integration Tests**:
  - Test the `AutorouteTool` flow with mocked Routing Service.
  - Verify the output string contains expected details.

## Definition of Done

- [ ] `AutorouteTool` registered and callable.
- [ ] Data fetching logic is correct (respects date).
- [ ] Connects to `RoutingService`.
- [ ] Returns a clear, human-readable preview.

## Activity Log

- 2026-01-21T10:23:53Z – Antigravity – shell_pid=4007482 – lane=doing – Started implementation via workflow command
- 2026-01-21T11:50:59Z – Antigravity – shell_pid=4007482 – lane=for_review – Ready for review: Implemented AutorouteTool with timing extraction from ORS and accurate preview display.
