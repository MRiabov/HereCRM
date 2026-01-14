---
work_package_id: WP05
slug: verification
lane: planned
subtasks: [T016, T017, T018]
history:
  - date: 2026-01-14
    event: Created work package prompt.
---

# WP05: Verification and Polish

## Objective

Verify the entire feature implementation against the requirements and ensure quality.

## Context

This is the final phase to ensure zero regressions and that all user stories from Spec 002 are fulfilled.

## Subtasks

### T016: Unit Tests (State Transitions)

- **File**: `tests/test_pipeline_logic.py`
- **Tests**: Mock the EventBus and verify that the handlers update customer state correctly based on mock job payloads.

### T017: Integration Tests (User Stories)

- **File**: `tests/test_pipeline_integration.py`
- **Tests**:
  - Create lead -> verify state.
  - Add job -> verify state change.
  - Add second job -> verify state change.
  - Mark as Lost -> Add job -> verify state returns to active.

### T018: Search & Filter Tests

- **File**: `tests/test_crm_search_pipeline.py`
- **Tests**: Populate customers in different stages and verify search results for each filter.

## Definition of Done

- All new tests pass.
- No regressions in existing CRM functionality.
- Feature matches the success criteria in Spec 002.
