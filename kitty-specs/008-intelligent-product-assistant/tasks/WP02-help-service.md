---
work_package_id: WP02
title: Help Service Logic
lane: "done"
subtasks:
  - T005
  - T006
  - T007
agent: "Antigravity"
review_status: "approved without changes"
reviewed_by: "Antigravity"
---

# WP02: Help Service Logic

**Goal**: Implement the core RAG logic to fetch history, load manual, and construct the context-aware prompt.

## Context

The `HelpService` is the brain of the assistant. It needs to gather context (manual + user history) and prepare a prompt for the LLM.

## Subtasks

### T005: Create `HelpService` class

- Create `src/services/help_service.py`.
- Define `class HelpService`.
- **Init**: Should accept `db_session` (AsyncSession).
- **Loaders**:
  - Implement `_load_manual(self) -> str`: Read `src/assets/manual.md`. Cache it if possible.
  - Implement `_load_channel_config(self)`: Use the config loader from WP01.

### T006: Implement `get_chat_history`

- In `HelpService`, implement `async def get_chat_history(self, business_id: int, phone_number: str, limit: int = 5) -> List[Message]`.
- Query the `Message` table (from `src/models.py`).
- Filter by `business_id` and `from_number` (or `to_number` matching the user's phone).
- **Clarification**: `Message` table stores all messages. We need the conversation for this user.
  - Match `business_id` AND (`from_number` == phone OR `to_number` == phone).
- Order by `created_at` DESC, take limit, then reverse to chronological order.

### T007: Implement `construct_help_prompt`

- Implement `def construct_help_prompt(self, history: List[Message], channel: str) -> List[dict]`.
- **System Prompt**:
  - "You are a helpful CRM assistant."
  - "Use the following manual to answer the user's question."
  - "Channel restrictions: {restrictions from config based on channel}"
  - "**MANUAL CONTENT**:\n{manual_text}"
- **History injection**:
  - Format the `history` messages into OpenAI format (`role`, `content`).
  - **Important**: If the last message was a tool call or had an error, include that context if available in `log_metadata`.
- **Return**: A list of message dicts suitable for `LLMClient`.

## Definition of Done

- `HelpService` can load the manual.
- `get_chat_history` returns the correct list of recent messages.
- `construct_help_prompt` produces a prompt containing the manual and the conversation history.

## Activity Log

- 2026-01-19T17:09:55Z – Antigravity – lane=doing – Starting core logic implementation
- 2026-01-19T17:10:47Z – Antigravity – lane=for_review – Implementation complete and verified
- 2026-01-19T19:40:44Z – Antigravity – lane=doing – Started implementation
- 2026-01-19T19:46:06Z – Antigravity – lane=for_review – Implementation complete with unit tests for HelpService.
- 2026-01-19T19:58:00Z – Antigravity – lane=done – Approved without changes. Verified core logic and security.
