# Research: Pipeline Progression Logic

**Status**: Completed
**Date**: 2026-01-14

## Design Decisions

### 1. State Management Pattern

- **Decision**: Use a lightweight `EventBus` (Observer pattern).
- **Rationale**: Decouples `JobService` from `CustomerService`. Prevents circular dependencies where `JobService` needs to import `CustomerService` to update stages. Allows future extensibility (e.g., sending notifications on stage change).
- **Alternatives**:
  - *Direct Service Calls*: Tightly couples services, harder to test in isolation.
  - *Database Triggers*: Overkill for in-memory/JSON storage, adds complexity.

### 2. Pipeline Stage Storage

- **Decision**: Hardcoded Python `Enum`.
- **Rationale**: Provides type safety and easy refactoring in IDE. Sufficient for current requirements where users don't need to define custom stages dynamically.
- **Alternatives**:
  - *Database Table*: Allows dynamic configuration but adds significant complexity (CRUD for stages, foreign keys).

### 3. Visualization

- **Decision**: Text-based list output.
- **Rationale**: Fits the "WhatsApp-first" text interface.
- **Alternatives**:
  - *Image Generation*: Too slow/complex for this iteration.
