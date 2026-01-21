# Work Packages: Autoroute Optimization

**Feature**: 013-autoroute-optimization

## Setup & Foundations (Phase 1)

### [ ] WP01: Database Migrations & Models

- **Goal**: Establish the data models required for availability and routing optimizations.
- **Priority**: Critical (Foundation)
- **Subtasks**:
  - [x] T001: Create `CustomerAvailability` model and migration
  - [x] T002: Update `User` model with start location fields
  - [x] T003: Update `Job` and `Service` with duration fields
  - [x] T004: Implement `AvailabilityService` basics
- **Dependencies**: None
- **Prompt Size**: ~300 lines

### [ ] WP02: Routing Service Infrastructure

- **Goal**: Implement the routing logic core, including ORS integration and Mock fallback.
- **Priority**: High
- **Subtasks**:
  - [x] T005: Define `RoutingServiceProvider` interface
  - [x] T006: Implement `MockRoutingService`
  - [x] T007: Implement `OpenRouteServiceAdapter` request builder
  - [x] T008: Implement `OpenRouteServiceAdapter` response parser
  - [x] T009: Integration test for Routing Service
- **Dependencies**: WP01
- **Prompt Size**: ~450 lines

## Implementation (Phase 2)

### [ ] WP03: Autoroute Command - Preview

- **Goal**: Implement the read-only portion of the `autoroute` command (fetch data using new models, call service, display result).
- **Priority**: High
- **Subtasks**:
  - [x] T010: Scaffold `autoroute` command
  - [x] T011: Implement data fetching (Jobs, Employees, Availability)
  - [x] T012: Integrate `RoutingService` execution
  - [x] T013: Implement Preview display (text table)
- **Dependencies**: WP02
- **Prompt Size**: ~350 lines

### [ ] WP04: Autoroute Command - Execution

- **Goal**: Complete the command by adding the interactive confirmation and transaction application logic.
- **Priority**: Medium
- **Subtasks**:
  - [ ] T014: Add interactive confirmation prompt
  - [ ] T015: Implement `apply_schedule` transaction logic
  - [ ] T016: Add notification hooks (placeholder)
- **Dependencies**: WP03
- **Prompt Size**: ~250 lines
