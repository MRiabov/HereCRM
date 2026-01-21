# Implementation Plan - Autoroute Optimization

## Problem to Solve

Business owners want to automate the scheduling of service jobs to minimize travel time and maximize efficiency, while respecting customer availability windows. Currently, scheduling is manual and inefficient.

## Technical Context

We will implement a `RoutingService` that solves the Vehicle Routing Problem (VRP). The system needs to manage customer availability and use this constraint during optimization.

**Constraints:**

- **Routing Engine**: OpenRouteService (primary), Mock implementation (dev/test).
- **Data Model**: Relational storage for customer availability (not JSON).
- **Performance**: < 10 seconds for < 50 jobs.

## Proposed Architecture

### 1. Data Model Updates

Instead of a JSON column, we will introduce a dedicated table for availability to allow easier querying and referential integrity.

**New Model: `CustomerAvailability`**

- `id`: Integer, PK
- `customer_id`: FK to `Customer`
- `start_time`: DateTime (UTC)
- `end_time`: DateTime (UTC)
- `is_available`: Boolean (default True, allows explicit "unavailable" blocks if needed later)

**Updates to `User`**

- `default_start_location_lat`: Float
- `default_start_location_lng`: Float

**Updates to `Job` & `Service`**

- `estimated_duration`: Integer (minutes)

### 2. Routing Service

We will define a `RoutingServiceProvider` abstract base class to allow swapping implementations.

- `calculate_routes(jobs: List[Job], employees: List[User]) -> RoutingSolution`

**Implementations:**

1. `OpenRouteServiceAdapter`: Integration with live ORS API VRP endpoint.
2. `MockRoutingService`: Local implementation using Haversine distance for "as the crow flies" optimization (User Request).

### 3. Command Interface (`autoroute`)

- **Input**: Date (default: today).
- **Logic**:
    1. Fetch unassigned jobs for the date.
    2. Fetch available employees.
    3. Fetch `CustomerAvailability` for customers related to these jobs.
    4. Call `RoutingService`.
    5. Present preview to user.
- **Confirmation**:
  - User confirms -> DB updates committed.

## Work Packages

### Phase 1: Core Data & Services

- **WP01**: Database Migrations & Models
  - Create `CustomerAvailability` model.
  - Update `User`, `Job`, `Service` models.
  - API/Service methods to manage availability (CRUD).

- **WP02**: Routing Service Infrastructure
  - Define `RoutingService` interface.
  - Implement `MockRoutingService` (simple distance-based sort/assign).
  - Implement `OpenRouteServiceAdapter` (client, payload builder, response parser).

- **WP03**: Autoroute Command Logic
  - Implement `autoroute [date]` logic.
  - Fetch data, invoke service, format output preview.

- **WP04**: Confirmation & Execution
  - Implement "apply schedule" logic transaction.
  - Notifications (placeholder/hook).

## Risks & Mitigations

- **ORS Reliability**: API limits or downtime. *Mitigation*: Fallback to manual scheduling or Mock service locally.
- **Geocoding Accuracy**: Start locations must be valid coords. *Mitigation*: Reuse existing `GeocodingService` to validate addresses on save.
