# Tasks: Advanced Search

**Details**:

- **Feature Branch**: `005-unified-search`
- **Spec**: [spec.md](spec.md)
- **Plan**: [plan.md](plan.md)

## Work Packages

### WP01: Foundation & Service Skeleton

- **Status**: [ ]
- **Goal**: Establish the `SearchService` and update data models to support the new search definition.
- **Priority**: High (Blocker)
- **Subtasks**:
  - [ ] T001: Create `SearchService` class with dependency injection
  - [ ] T002: Update `SearchTool` model with `detailed` flag and `pipeline_stage`

    # For SearchTool model (likely in src/uimodels.py)

    # detailed: bool = False # [NEW]

    # pipeline_stage: Optional[str] # [ALREADY MERGED FROM 002]

    # service_query: Optional[str] # [NEW] Filter entities by service performed

    # ... existing fields

  - [ ] T003: Create basic unit tests for Service instantiation
- **Implementation Sketch**: Scaffold `src/services/search_service.py`. Update `src/uimodels.py`. Create `tests/test_search_service.py`.
- **Dependencies**: None

### WP02: Text Search & Attribute Filtering

- **Status**: [ ]
- **Goal**: Enable core text search and attribute filtering for Customers, Requests, and Jobs (non-spatial).
- **Priority**: High
- **Subtasks**:
  - [ ] T004: Implement `_search_customers` in `SearchService` (including stage filtering)
  - [ ] T005: Implement `_search_requests` in `SearchService`
  - [ ] T006: Implement `_search_jobs` (text/attribute only) in `SearchService`
  - [ ] T007: Implement `_search_services` (Search Catalog) in `SearchService`
  - [ ] T008: Implement service-based entity filtering (Find Customers/Jobs by service performed)
  - [ ] T009: Implement unified aggregation logic in `SearchService.search`
  - [ ] T010: Add unit tests for aggregation and repo delegation
- **Implementation Sketch**: focusing on wiring the `SearchService` to existing repository `search` methods. Logic to combine results if `entity_type` is missing.
- **Dependencies**: WP01

### WP03: Proximity Search

- **Status**: [ ]
- **Goal**: Implement spatial search capability for Jobs (and Customers) using Geocoding and Python-side filtering.
- **Priority**: High
- **Subtasks**:
  - [ ] T010: Implement `GeocodingService` integration in `SearchService`
  - [ ] T011: Implement spatial filtering logic in `JobRepository.search`
  - [ ] T012: Update `SearchService` to handle location parameters and pass to Repos
  - [ ] T013: Add Generic Proximity handling (search all entities near location)
  - [ ] T014: Add integration tests for Proximity Search
- **Implementation Sketch**: Use `geocoding.py` to get lat/long. Add Haversine distance check in `JobRepository` (since it's SQLite) to filter results post-query or during query if possible (likely post-query for simplicity/compatibility).
- **Dependencies**: WP02

### WP04: Formatting, UX & Pagination

- **Status**: [ ]
- **Goal**: Ensure search results are presented correctly (Detailed vs Concise) and adhere to platform limits.
- **Priority**: Medium
- **Subtasks**:
  - [ ] T015: Implement `_format_detailed` and `_format_concise` methods
  - [ ] T016: Implement Pagination/Truncation logic (Hard limit 10)
  - [ ] T017: Verify Detailed/Concise toggling in tests
  - [ ] T018: Verify Result Truncation in tests
- **Implementation Sketch**: Add formatting helpers in `SearchService`. Enforce list slicing `[:10]` at the end of `search`.
- **Dependencies**: WP02

### WP05: Integration & Cleanup

- **Status**: [ ]
- **Goal**: Wire up the new service to the Tool Executor and verify end-to-end functionality.
- **Priority**: Medium
- **Subtasks**:
  - [ ] T019: Inject `SearchService` into `ToolExecutor`
  - [ ] T020: Replace `ToolExecutor._execute_search` with `SearchService` call
  - [ ] T021: Update `LLMClient` prompts/instructions for new search params
  - [ ] T022: Run full E2E/Integration tests
  - [ ] T023: Remove legacy search code from `ToolExecutor`
- **Implementation Sketch**: Final wiring. Ensure the agent actually calls the new service.
- **Dependencies**: WP04, WP03
