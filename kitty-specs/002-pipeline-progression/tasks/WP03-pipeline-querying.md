---
work_package_id: WP03
slug: pipeline-querying
lane: "for_review"
subtasks: [T009, T010, T011]
agent: "codex"
history:
  - date: 2026-01-14
    event: Created work package prompt.
---

# WP03: Pipeline Querying and Reporting

## Objective

Provide visibility into the sales pipeline via natural language queries.

## Context

The user wants to see "the health of the sales funnel". This means getting counts per stage and potentially a list of customers in those stages.

## Subtasks

### T009: CRM Service Summary Method

- **File**: `src/services/crm_service.py`
- **Action**: Implement `get_pipeline_summary()`.
- **Output**: A data structure grouping customers by `PipelineStage` with counts.

### T010: Visualization

- **Action**: Implement a text-based/markdown formatter for the pipeline summary.
- **Requirement**: Should show:

  ```
  ### Pipeline Breakdown
  - **Not Contacted**: 5 customers
  - **Contacted**: 2 customers
  - **Converted Once**: 10 customers
  ...
  ```

- **Included Details**: For each stage, list names of customers (or top N if many).

### T011: LLM Tool Integration

- **File**: `src/llm_client.py`
- **Action**: Add or update a tool (e.g., `GetPipelineTool`) that allows the LLM to fetch this summary when the user asks "show me our pipeline".

## Definition of Done

- User can ask "how is our pipeline doing?" and get a formatted response.
- Response includes counts per stage.
- Performance is <3s as per performance goals.

## Activity Log

- 2026-01-14T21:03:28Z – codex – lane=doing – Started implementation
- 2026-01-14T21:07:14Z – codex – lane=for_review – Ready for review
