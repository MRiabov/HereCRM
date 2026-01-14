---
work_package_id: WP04
slug: search-and-manual-updates
lane: planned
subtasks: [T012, T013, T014, T015]
history:
  - date: 2026-01-14
    event: Created work package prompt.
---

# WP04: Search Filtering and Manual Updates

## Objective

Enable explicit control and filtering of the pipeline stages.

## Context

Sometimes automatic inference isn't enough (e.g., marking a customer as "Lost" manually). Also, users need to filter search results by these stages.

## Subtasks

### T012: Repository Filtering

- **File**: `src/repositories.py` (CustomerRepository)
- **Action**: Update `search` method to accept an optional `pipeline_stage` filter.
- **Logic**: If provided, return only customers in that stage.

### T013: Update Search Tool

- **File**: `src/uimodels.py` / `src/llm_client.py`
- **Action**: Update the search tool definition to include `pipeline_stage` as an optional parameter.
- **Prompting**: Guide the LLM to use this when the user says "show me customers in Lost stage".

### T014: Manual Status Tool

- **File**: `src/services/crm_service.py`
- **Action**: Add a method `update_customer_stage(customer_id, stage)`.
- **Validation**: Ensure stage is a valid `PipelineStage`.

### T015: Manual Update LLM Integration

- **Action**: Expose the manual update capability to the LLM.
- **Example Usage**: "Mark John as Lost", "John is not interested anymore".

## Definition of Done

- Searching specifically for a stage works correctly.
- Customers can be moved to "Lost" or "Not Interested" via text command.
- Stage updates are reflected in the pipeline summary (WP03).
