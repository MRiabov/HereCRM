# Research & Decisions

## Availability Storage

**Decision**: Relational Table (`CustomerAvailability`)
**Rationale**:

- User explicitly requested "python models" (SQLAlchemy) over JSON.
- Allows standard SQL querying for "customers available between X and Y".
- Enforces referential integrity (FK to Customer).
**Alternatives Considered**:
- JSON column (Originally proposed, rejected by user).
- RFC 5545 RRule (Too complex for MVP, user preferred specific date ranges).

## Routing Engine

**Decision**: OpenRouteService (Production) + Mock Service (Dev/Test)
**Rationale**:

- Mock service prevents draining API limits during development.
- Mock logic: Euclidean/Haversine distance (User suggestion).
- Live service: OpenRouteService VRP endpoint is the standard for this project.
**Implementation Detail**:
- A `RoutingService` protocol/abstract base class will allow switching via config (`ROUTING_PROVIDER=mock`).

## Authorization

**Decision**: Business Owner & Employee Access
**Rationale**:

- Owners trigger global optimization.
- Employees can view/update their own start locations.
