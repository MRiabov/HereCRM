---
work_package_id: "WP02"
title: "Routing Service Infrastructure"
lane: "for_review"
dependencies: ["WP01"]
subtasks:
  - "T005"
  - "T006"
  - "T007"
  - "T008"
  - "T009"
agent: "Antigravity"
shell_pid: "4007002"
---

# Work Package 02: Routing Service Infrastructure

## Objective

Implement the core routing logic, including the abstract interface, a Mock implementation for testing, and the OpenRouteService (ORS) integration.

## Context

The system needs to optimize routes using an external API (ORS). To ensure testability and resilience, we use an Adapter pattern.

## Subtasks

### T005: Define `RoutingServiceProvider` interface

**Purpose**: Define the contract for routing services.
**Files**: `src/services/routing/base.py`, `src/core/types.py` (if needed for shared types)
**Steps**:

1. Create directory `src/services/routing/`.
2. Define `RoutingSolution` dataclass:
    - `routes`: Dict[int, List[Job]] (Employee ID -> Ordered List of Jobs).
    - `unassigned_jobs`: List[Job].
    - `metrics`: Dict (e.g., total_distance, total_duration).
3. Define `RoutingServiceProvider(ABC)`:
    - `calculate_routes(jobs: List[Job], employees: List[User]) -> RoutingSolution`.
    - `validate_locations(locations: List[Location])` (optional, for validation).

### T006: Implement `MockRoutingService`

**Purpose**: Provide a fast, local implementation for Development and Testing without hitting API limits.
**Files**: `src/services/routing/mock.py`
**Steps**:

1. Implement `MockRoutingService(RoutingServiceProvider)`.
2. Logic:
    - Simple greedy assignment or round-robin using Haversine distance.
    - Or even simpler: assign jobs to the nearest employee based on straight-line distance.
    - Should respect `CustomerAvailability` if easily possible, otherwise ignore for Mock (or stub it). *Better to respect it simply: check if time overlaps with availability.*

### T007: Implement `OpenRouteServiceAdapter` request builder

**Purpose**: Construct the JSON payload for ORS VRP endpoint.
**Files**: `src/services/routing/ors.py`
**Steps**:

1. Add `OPENROUTESERVICE_API_KEY` to `src/config.py` (and `.env.example`).
2. Implement `OpenRouteService.build_payload(jobs, employees)`:
    - Map `User` (Employee) to `vehicles`.
    - Map `Job` to `jobs` (deliveries/services).
    - Include `time_windows` from `CustomerAvailability`.
    - Include `service_duration` from `Job/Service`.
    - Start/End locations from `User.default_start_location`.

### T008: Implement `OpenRouteServiceAdapter` response parser

**Purpose**: Parse ORS response back into domain objects.
**Files**: `src/services/routing/ors.py`
**Steps**:

1. Implement `OpenRouteService.parse_response(ors_response, original_jobs) -> RoutingSolution`.
    - Map ORS "routes" back to ordered lists of Jobs.
    - Identify unassigned jobs.
2. Implement `calculate_routes` method utilizing `build_payload`, `requests.post`, and `parse_response`.
    - Handle API errors (timeouts, 4xx, 5xx) gracefully (raise `RoutingException`).

### T009: Integration test for Routing Service

**Purpose**: Verify the adapter works (using VCR or Mocks).
**Files**: `tests/services/test_routing.py`
**Steps**:

1. Test `MockRoutingService` logic (unit test).
2. Test `OpenRouteService` integration:
    - Mock the network call (request/response).
    - Verify payload structure matches ORS VRP spec.
    - Verify response parsing correctly builds `RoutingSolution`.

## Test Strategy

- **Unit Tests**: Heavy focus on `build_payload` correctness and `parse_response` logic.
- **Mocking**: Do NOT make real API calls in CI. Use `vcrpy` or `responses`.

## Definition of Done

- [ ] `src/services/routing/` package structure created
- [ ] `RoutingSolution` and `RoutingServiceProvider` defined
- [ ] `MockRoutingService` implemented and working
- [ ] `OpenRouteServiceAdapter` implemented (payload & parsing)
- [ ] API Key configuration added
- [ ] Tests passing for both implementations

## Activity Log

- 2026-01-21T09:46:07Z – Antigravity – shell_pid=4007002 – lane=doing – Started implementation via workflow command
- 2026-01-21T09:52:31Z – Antigravity – shell_pid=4007002 – lane=for_review – Ready for review: Implemented Routing Service Infrastructure including Mock and ORS adapters.
