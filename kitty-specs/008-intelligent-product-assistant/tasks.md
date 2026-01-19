# Implementation Tasks: Intelligent Product Assistant

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Overview

Total Work Packages: 4
Total Subtasks: 14

## Work Packages

### WP01: Infrastructure & Configuration (Setup)

**Goal**: Establish the configuration headers and base classes required for channel-specific behavior and raw LLM text generation.
**Priority**: P0 (Blocker)

- [x] **T001**: Create `src/assets/channels.yaml` with default response length configurations for `whatsapp` and `email`. [P]
- [x] **T002**: Implement `ChannelConfig` loader in `src/config.py` to parse `channels.yaml`. [P]
- [x] **T003**: Update `LLMClient` in `src/llm_client.py` to add `chat_completion` method for non-tool-calling text generation.
- [x] **T004**: Provision `src/assets/manual.md` by copying content from `kitty-specs/008-intelligent-product-assistant/manual.md`.

### WP02: Help Service Logic (Foundation)

**Goal**: Implement the core RAG logic to fetch history, load manual, and construct the context-aware prompt.
**Priority**: P1 (Core Logic)

- [x] **T005**: Create `src/services/help_service.py` and implement `load_manual` and `load_channel_config`. [P] (See: [WP02-help-service.md](tasks/WP02-help-service.md))
- [x] **T006**: Implement `get_chat_history` method in `HelpService` to retrieve last 5 `Message` records for a given user/business using SQLAlchemy.
- [x] **T007**: Implement `construct_help_prompt` method to combine system instructions, manual content, and chat history into a prompt string. [P]

### WP03: Integration & Execution (Feature)

**Goal**: Wire the Help Service into the application flow via the `HelpTool` and ensure responses are generated using the LLM.
**Priority**: P1 (Feature Complete)

- [ ] **T008**: Implement `generate_help_response` in `HelpService` that orchestrates the prompt construction and calls `LLMClient.chat_completion`.
- [ ] **T009**: Update `WhatsappService` (or `ToolExecutor`) to intercept `HelpTool` calls and delegate them to `HelpService.generate_response`.
- [ ] **T010**: Ensure `HelpResult` (or string output) is correctly formatted and returned to the user through the messaging pipeline.

### WP04: Channel Adaptation & Polish (Polish)

**Goal**: Refine the output based on channel constraints and ensure robust error handling.
**Priority**: P2 (Refinement)

- [ ] **T011**: Enhance `HelpService` to respect `max_length` from `ChannelConfig` when generating responses.
- [ ] **T012**: Implement specific error handling for when the manual is missing or empty (fallback message).
- [ ] **T013**: Handle `LLMParser` failures by passing the error context to `HelpService` if the user asks "Why did that fail?".
- [ ] **T014**: Verify `manual.md` content covers the scenarios in User Story 1 & 2.
