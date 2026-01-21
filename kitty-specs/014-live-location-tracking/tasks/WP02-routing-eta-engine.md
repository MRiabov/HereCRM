---
work_package_id: "WP02"
subtasks:
  - "T006"
  - "T007"
  - "T008"
  - "T009"
title: "Routing - ETA Engine & ORS Client"
phase: "Phase 1 - Core Location Infrastructure"
lane: "doing"
dependencies: ["WP01"]
agent: "Antigravity"
shell_pid: "4035720"
history:
  - timestamp: "2026-01-21T10:21:37Z"
    lane: "planned"
    agent: "antigravity"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 – Routing - ETA Engine & ORS Client

## Objectives & Success Criteria

- Integration with OpenRouteService (ORS) Routing API.
- Implementation of `RoutingService` to calculate travel time (minutes) between points.
- Reliable rounding logic for customer-facing ETA (nearest 5 minutes).

## Context & Constraints

- Supporting docs: `kitty-specs/014-live-location-tracking/plan.md`.
- Dependent on: ORS API Key (should be in env vars).
- Reuses patterns from Spec 013 (Autoroute) if any `RoutingService` code is available in `main`.

## Subtasks & Detailed Guidance

### Subtask T006 – RoutingService skeleton

- **Purpose**: Centralize all routing logic.
- **Steps**:
  1. Create `src/services/routing_service.py`.
  2. Define `RoutingService` class.
  3. Prepare for integration with ORS.
- **Files**: `src/services/routing_service.py`

### Subtask T007 – Implement OpenRouteServiceAdapter

- **Purpose**: Communicate with the ORS API.
- **Steps**:
  1. Implement a method `get_driving_duration(origin_lat, origin_lng, dest_lat, dest_lng) -> float (seconds)`.
  2. Use `httpx` for async API calls.
  3. API Endpoint: `POST /v2/directions/driving-car`.
  4. Handle API errors and timeouts gracefully.
- **Files**: `src/services/routing_service.py`

### Subtask T008 – ETA Rounding logic

- **Purpose**: Format duration for customer friendliness.
- **Steps**:
  1. Implement `RoutingService.get_eta_minutes(...)`.
  2. Logic: Convert seconds to minutes, then `ceil(minutes / 5) * 5`.
  3. Return an integer representing minutes.
- **Files**: `src/services/routing_service.py`

### Subtask T009 – ORS Mocks for local testing

- **Purpose**: Allow deterministic testing without hitting the real API.
- **Steps**:
  1. Add a `MockRoutingService` or `MockORSClient`.
  2. Ensure unit tests for `RoutingService` can run offline.
- **Files**: `tests/unit/test_routing_service.py`

## Definition of Done Checklist

- [ ] `RoutingService` can return an ETA in minutes.
- [ ] Rounding logic passes unit tests (e.g., 7 mins -> 10 mins).
- [ ] ORS API integration handles network failures without crashing.
- [ ] `tasks.md` updated with status change.

## Review Guidance

- Check that the ORS API key is loaded from the correct environment variable.
- Verify that coordinates are sent in the correct order (ORS often uses [lon, lat]).

## Activity Log

- 2026-01-21T10:21:37Z – antigravity – lane=planned – Prompt created.
- 2026-01-21T10:51:43Z – Antigravity – shell_pid=4035720 – lane=doing – Started review via workflow command
- 2026-01-21T10:54:21Z – Antigravity – shell_pid=4035720 – lane=planned – Wrong spec - reviewing 013-WP02 instead
- 2026-01-21T11:06:05Z – Antigravity – shell_pid=4035720 – lane=doing – Started implementation via workflow command
