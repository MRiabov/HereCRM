---
work_package_id: WP05
subtasks:
  - T018
  - T019
  - T020
  - T021
  - T022
lane: planned
history:
  - date: 2026-01-19
    action: created
---

# WP05 - Channel Logic & Auto-Confirmation

## Objective

Implement intelligent channel behavior: configuration, conciseness strategies, and auto-confirmation.

## Context

Different channels have different costs and user expectations. SMS should be short and cost-effective (auto-confirm). Email can be longer.

## Subtasks

### T018: Channel Configuration

- Create `src/config/channels.yaml` (or similar).
- Structure:

  ```yaml
  channels:
    sms:
      provider: twilio
      auto_confirm: true
      auto_confirm_timeout: 45
      max_length: 160
    email:
      provider: postmark
      auto_confirm: true
      auto_confirm_timeout: 45
      max_length: 10000
    whatsapp:
      provider: meta
      auto_confirm: false
  ```

- Implement loader to read this config.

### T019: Auto-Confirmation Mechanism

- State machine update: When a tool call is proposed, check `active_channel` config.
- If `auto_confirm` is true:
  - Schedule a job or check timestamp on next tick.
  - If `timeout` passes (45s) and no user input ("NO", "CANCEL") is received, execute the tool.

### T020: Integrate with ToolExecutor

- Modify `Agent` loop or `ToolExecutor` to handle "Pending Auto-Confirm" state.
- Ensure user can interrupt.

### T021: Conciseness Logic

- In `LLMClient` or `ResponseManager`, check `max_length` for the channel.
- If channel is SMS, append system instruction to LLM: "Keep response under 160 chars".
- Or post-process/truncate (risky for context). Better to prompt LLM.

### T022: End-to-End Verification

- Verify the full flow:
  1. User sends SMS -> Twilio -> Webhook -> System.
  2. System plans tool -> waits 45s -> Auto-confirms -> Executes.
  3. System sends result -> Twilio -> SMS (concise).

## Test Strategy

- **Manual**: Use the `manual.md` checklist (to be updated) to verify timing and interruptions.
- **Unit**: Test config loader. Test auto-confirm logic with fake clock.
