---
work_package_id: WP05
subtasks:
  - T018
  - T019
  - T020
  - T021
  - T022
lane: "done"
agent: "Antigravity"
---
# Work Package: Integration & Cleanup

## Objective

Wire up the new service.

## Context

Final step to make the feature live.

## Implementation Steps

1. **[T018] Inject Service**
   - Update `ToolExecutor.__init__` to accept `SearchService`.

2. **[T019] Update ToolExecutor**
   - Modify `_execute_search` to call `self.search_service.search(...)`.

3. **[T020] Update LLMClient**
   - Review and update system prompt to ensure `detailed` flag and `location` are extracted.

4. **[T021] E2E Tests**
   - Run `tests/test_tool_executor.py` (or similar) to verify full flow.
   - Run manual verification script if available.

5. **[T022] Cleanup**
   - Remove legacy search code from `ToolExecutor`.

## Verification

- Run `pytest`

## Activity Log

- 2026-01-17T10:45:40Z – Antigravity – lane=doing – Injecting Service
- 2026-01-17T10:48:23Z – Antigravity – lane=done – Integration verified with tests
