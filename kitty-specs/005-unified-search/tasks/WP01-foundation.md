---
work_package_id: WP01
subtasks:
  - T001
  - T002
  - T003
lane: "done"
agent: "antigravity"
assignee: "antigravity"
shell_pid: "N/A"
review_status: "approved without changes"
reviewed_by: "antigravity"
---
# Work Package: Foundation & Service Skeleton

## Objective

Establish the `SearchService` and update data models to support the new search definition.

## Context

We are implementing a unified search service. This WP sets up the class structure and dependency injection to avoid "God Class" problems in `ToolExecutor`.

## Implementation Steps

1. **[T001] Create SearchService**
   - File: `src/services/search_service.py`
   - Class: `SearchService`
   - Inject `CustomerRepository`, `JobRepository`, `RequestRepository`, `GeocodingService` in `__init__`.
   - Add empty `search` method.

2. **[T002] Update SearchTool**
   - File: `src/uimodels.py`
   - Update `SearchTool` pydantic model to include `detailed: bool = False`.

3. **[T003] Basic Tests**
   - File: `tests/test_search_service.py`
   - Details: Test that `SearchService` can be instantiated and `SearchTool` accepts the new flag.

## Verification

- Run `pytest tests/test_search_service.py`

## Activity Log

- 2026-01-16T17:05:18Z – antigravity – lane=doing – Started implementation
- 2026-01-16T17:06:53Z – antigravity – lane=for_review – Ready for review
- 2026-01-16T17:21:00Z – antigravity – lane=done – Approved without changes
