---
work_package_id: WP03
title: LLM Tool Integration
lane: "doing"
dependencies: []
subtasks: [T011, T012, T013, T014]
agent: "antigravity"
assignee: "Antigravity"
shell_pid: "3957729"
reviewed_by: "MRiabov"
review_status: "approved"
---

### Objective

Expose the Quote creation functionality to the AI Agent so it can be triggered by natural language requests like "Send a quote to John for cleaning".

### Context

The system uses `llm_client.py` and `tools/*.py` to map intentions to functions. We need a new tool `CreateQuoteTool`.

### Subtasks

#### T011: Define Tool Input Schema

**Purpose**: Structure the parameters the LLM needs to extract.
**Steps**:

1. Edit `src/uimodels.py`.
2. Define `QuoteLineItemInput(BaseModel)`: description, quantity, price.
3. Define `CreateQuoteInput(BaseModel)`:
   - `customer_identifier`: Name or Phone to lookup.
   - `items`: List[QuoteLineItemInput].

#### T012: Implement Tool Wrapper

**Purpose**: The executable logic for the tool.
**Steps**:

1. Create/Edit `src/tools/quote_tools.py`.
2. Create `CreateQuoteTool` class.
3. Implement `run(input: CreateQuoteInput)`:
   - Resolve `customer_identifier` using `SearchService` or similar.
   - If ambiguous or not found, return error string asking for clarification.
   - If found, call `QuoteService.create_quote` then `QuoteService.send_quote`.
   - Return success message "Quote sent to {name} via WhatsApp."

#### T013: Register Tool

**Purpose**: Make it available to the Agent.
**Steps**:

1. Edit `src/llm_client.py` (or `tool_registry.py`).
2. Add `CreateQuoteTool` to the list of available tools.
3. Ensure the system prompt or tool descriptions guide the LLM to use it for "quote" requests.

#### T014: Tool Test

**Purpose**: Verify LLM input maps to Service call.
**Steps**:

1. Add test in `tests/unit/test_quote_tools.py`.
2. Create `CreateQuoteTool` instance with mocked services.
3. Pass valid input.
4. Verify `create_quote` and `send_quote` are called.

### Verification

- Run `pytest tests/unit/test_quote_tools.py`.

## Activity Log

- 2026-01-20T19:08:39Z – Antigravity – shell_pid=3779362 – lane=doing – Started implementation via workflow command
- 2026-01-20T19:14:08Z – Antigravity – shell_pid=3779362 – lane=for_review – Ready for review: Implemented CreateQuoteTool and handler. Updated LLM client and ToolExecutor. Added unit tests.
- 2026-01-20T19:50:38Z – Antigravity – shell_pid=3779362 – lane=doing – Started review via workflow command
- 2026-01-20T19:51:54Z – Antigravity – shell_pid=3779362 – lane=done – Review passed: CreateQuoteTool implemented, registered in LLM client and prompts, with passing unit tests.
- 2026-01-21T07:24:06Z – antigravity – shell_pid=3957729 – lane=doing – Started implementation via workflow command
