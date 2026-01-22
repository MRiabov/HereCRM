# Research: Business Workflow Defaults

Path: kitty-specs/019-business-workflow-defaults/research.md

## Research Tasks

### 1. Data Model Migration for settings

- **Decision**: Add `settings: Mapped[dict] = mapped_column(JSON, default=dict)` to `Business` model.
- **Rationale**: The specification requires storing workflow preferences per business. Using a JSON field provides flexibility for future settings without repeated schema changes.
- **Alternatives considered**: Separate `WorkflowSetting` table (too complex for current needs), separate columns (less flexible).

### 2. Centralized Workflow Service

- **Decision**: Create `src/services/workflow.py` with `WorkflowSettingsService`.
- **Rationale**: Decouples business logic from data access. Allows for easy caching and unit testing of workflow rules.
- **Alternatives considered**: Direct database access in tools (results in code duplication).

### 3. Dynamic Message Filtering

- **Decision**: Use `src/assets/messages.yaml` templates and filter them in the message rendering logic by passing the business settings context.
- **Rationale**: Keeps the codebase clean while allowing the conversational UI to adapt to the business's chosen workflow.
- **Alternatives considered**: LLM-only filtering (less reliable, higher latency), hardcoded text blocks (not scalable).

### 4. Soft-blocking with Owner Override

- **Decision**: Implement a check in `src/tool_executor.py`. If a tool is disabled by workflow settings, return an interactive confirmation if user is OWNER.
- **Rationale**: Prevents accidental usage of disabled features while providing a path for "one-off" exceptions as requested by the user.
- **Alternatives considered**: Hard block only (too restrictive), no block (defeats the purpose of the setting).

## Technical Findings

- Existing `Business` model has `active_addons` as a JSON field.
- `src/assets/messages.yaml` already contains keys like `help_message` and `welcome_message` that need to be dynamic.
- `src/tool_executor.py` is the central point for tool dispatching.
- `src/uimodels.py` contains the `Business` owner/member logic.

## Remaining Unknowns

- [Resolved] Should UI be web-based or conversational? (Decision: Focus on conversational/WhatsApp initially).
- [Resolved] How to handle existing businesses? (Decision: Apply defaults on first access).
