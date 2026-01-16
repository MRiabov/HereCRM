# Tasks: Advanced Search

**Details**:

- **Feature Branch**: `005-unified-search`
- **Spec**: [spec.md](spec.md)
- **Plan**: [plan.md](plan.md)

## Work Packages

### WP01: Foundation & Service Skeleton

- **Status**: [x] (Implemented in [WP01-foundation.md](tasks/WP01-foundation.md))
- **Goal**: Establish the `SearchService` and update data models to support the new search definition.
- **Priority**: High (Blocker)
- **Subtasks**:
  - [x] T001: Create `SearchService` class with dependency injection
  - [x] T002: Update `SearchTool` model with `detailed` flag
  - [x] T003: Create basic unit tests for Service instantiation
- **Implementation Sketch**: Scaffold `src/services/search_service.py`. Update `src/uimodels.py`. Create `tests/test_search_service.py`.
- **Dependencies**: None

### WP02: Text Search & Attribute Filtering

- **Goal**: Enable core text search and attribute filtering for Customers, Requests, and Jobs (non-spatial).
- **Priority**: High
- **Subtasks**:
  - [x] T004: Implement `_search_customers` in `SearchService`
  - [x] T005: Implement `_search_requests` in `SearchService`
  - [x] T006: Implement `_search_jobs` (text/attribute only) in `SearchService`
  - [x] T007: Implement unified aggregation logic in `SearchService.search`
  - [x] T008: Add unit tests for aggregation and repo delegation
- **Implementation Sketch**: focusing on wiring the `SearchService` to existing repository `search` methods. Logic to combine results if `entity_type` is missing.
- **Dependencies**: WP01

### WP03: Proximity Search

- **Goal**: Implement spatial search capability for Jobs (and Customers) using Geocoding and Python-side filtering.
- **Priority**: High
- **Subtasks**:
  - [ ] T009: Implement `GeocodingService` integration in `SearchService`
  - [ ] T010: Implement spatial filtering logic in `JobRepository.search`
  - [ ] T011: Update `SearchService` to handle location parameters and pass to Repos
  - [ ] T012: Add Generic Proximity handling (search all entities near location)
  - [ ] T013: Add integration tests for Proximity Search
- **Implementation Sketch**: Use `geocoding.py` to get lat/long. Add Haversine distance check in `JobRepository` (since it's SQLite) to filter results post-query or during query if possible (likely post-query for simplicity/compatibility).
- **Dependencies**: WP02

### WP04: Formatting, UX & Pagination

- **Goal**: Ensure search results are presented correctly (Detailed vs Concise) and adhere to platform limits.
- **Priority**: Medium
- **Subtasks**:
  - [ ] T014: Implement `_format_detailed` and `_format_concise` methods
  - [ ] T015: Implement Pagination/Truncation logic (Hard limit 10)
  - [ ] T016: Verify Detailed/Concise toggling in tests
  - [ ] T017: Verify Result Truncation in tests
- **Implementation Sketch**: Add formatting helpers in `SearchService`. Enforce list slicing `[:10]` at the end of `search`.
- **Dependencies**: WP02

### WP05: Integration & Cleanup

- **Goal**: Wire up the new service to the Tool Executor and verify end-to-end functionality.
- **Priority**: Medium
- **Subtasks**:
  - [ ] T018: Inject `SearchService` into `ToolExecutor`
  - [ ] T019: Replace `ToolExecutor._execute_search` with `SearchService` call
  - [ ] T020: Update `LLMClient` prompts/instructions for new search params
  - [ ] T021: Run full E2E/Integration tests
  - [ ] T022: Remove legacy search code from `ToolExecutor`
- **Implementation Sketch**: Final wiring. Ensure the agent actually calls the new service.
- **Dependencies**: WP04, WP03
