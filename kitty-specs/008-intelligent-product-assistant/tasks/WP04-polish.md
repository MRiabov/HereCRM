---
work_package_id: WP04
title: Channel Adaptation & Polish
lane: planned
subtasks:
  - T011
  - T012
  - T013
  - T014
---

# WP04: Channel Adaptation & Polish

**Goal**: Refine the output based on channel constraints and ensure robust error handling.

## Context

Make the assistant feel native to the channel (short for WhatsApp) and robust against failures.

## Subtasks

### T011: Enforce Channel limits

- Update `construct_help_prompt` in `HelpService`.
- Add a system instruction: "Please keep your response under {max_length} characters as this is for {channel}." (Load `max_length` from config).
- Or use `max_tokens` param in `chat_completion` if applicable, but system prompt instruction is better for style.

### T012: Missing Manual Fallback

- In `HelpService.load_manual`:
  - If `manual.md` is empty or missing, return a default string: "I can't access my training manual right now, but I'm here to help! try 'add lead John Doe'."
  - Ensure the system doesn't crash.

### T013: Explain Failures

- If the user asks "Why did that fail?" (Story 2), the history will contain the error.
- **Task**: Ensure `construct_help_prompt` includes `log_metadata` from the last `Message` if it exists.
  - The `Message` model has `log_metadata`.
  - Format it into the context: "System Note: The previous request failed with error: {error_details}".

### T014: Verify Content

- Review `src/assets/manual.md`.
- Ensure it has sections answering:
  - "How do I add a lead?"
  - "How do I schedule a job?"
- If not, update `manual.md` with accurate instructions matching the current system capabilities.

## Definition of Done

- WhatsApp responses are concise (<150 chars preferrably).
- System handles missing manual gracefully.
- Assistant can explain "Why did that fail?" if the log contains the error.
- `manual.md` is populated with real instructions.
