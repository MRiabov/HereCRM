# Tasks: Multi-channel Communication

**Feature Branch**: `009-multi-channel-communication`
**Status**: Planned

## Work Packages

### WP01 - Data Model Refactor & Identity

**Goal**: Refactor User model to use Integer ID as PK and support Email. ensure data integrity.
**Priority**: P0 (Foundational)
**Dependencies**: None

- [ ] T001: Create migration to add `id` (PK) and `email` to `users` table. <!-- id: 0 -->
- [ ] T002: Migrate existing `users` to have valid IDs and preserve `phone_number`. <!-- id: 1 -->
- [ ] T003: Update `ConversationState` table to reference `user_id` instead of `phone_number`. <!-- id: 2 -->
- [ ] T004: Update `Messages` table to reference `user_id` (sender/receiver). <!-- id: 3 -->
- [ ] T005: Update codebase references to `user.phone_number` primary key usage to `user.id`. <!-- id: 4 -->
- [ ] T006: Verify data integrity for existing WhatsApp users. <!-- id: 5 -->

**Prompt**: [WP01-data-model-refactor.md](tasks/WP01-data-model-refactor.md)

---

### WP02 - SMS Channel Support (Twilio)

**Goal**: Implement sending and receiving SMS messages via Twilio.
**Priority**: P1
**Dependencies**: WP01

- [ ] T007: Implement `TwilioService` for sending SMS. <!-- id: 6 -->
- [ ] T008: Implement inbound Webhook handler for Twilio SMS. <!-- id: 7 -->
- [ ] T009: Link inbound SMS to `User` by `phone_number`. <!-- id: 8 -->
- [ ] T010: Update basic message routing to support SMS replies. <!-- id: 9 -->

**Prompt**: [WP02-sms-channel-twilio.md](tasks/WP02-sms-channel-twilio.md)

---

### WP03 - Email Channel Support (Postmark)

**Goal**: Implement sending and receiving Emails via Postmark.
**Priority**: P1
**Dependencies**: WP01

- [X] T011: Implement `PostmarkService` for sending Emails. <!-- id: 10 -->
- [X] T012: Implement inbound Webhook handler for Postmark (parse JSON). <!-- id: 11 -->
- [X] T013: Link inbound Email to `User` by `email` address. Create user if new (optional? verify spec). <!-- id: 12 -->
- [X] T014: Handle email threading headers (In-Reply-To, References). <!-- id: 13 -->

**Prompt**: [WP03-email-channel-postmark.md](tasks/WP03-email-channel-postmark.md)

---

### WP04 - Generic Webhook Integration

**Goal**: Allow external systems to inject messages via generic webhook.
**Priority**: P2
**Dependencies**: WP01

- [ ] T015: Create `GenericWebhook` endpoint (JSON schema validation). <!-- id: 14 -->
- [ ] T016: Implement logic to map webhook payload to `User` (by phone/email) and create `Message`. <!-- id: 15 -->
- [ ] T017: Test integration with mock payload. <!-- id: 16 -->

**Prompt**: [WP04-generic-webhook.md](tasks/WP04-generic-webhook.md)

---

### WP05 - Channel Logic & Auto-Confirmation

**Goal**: Implement channel-specific configuration, conciseness, and auto-confirmation flows.
**Priority**: P1
**Dependencies**: WP02, WP03

- [ ] T018: Create `ChannelConfig` YAML loader/structure. <!-- id: 17 -->
- [ ] T019: Implement `AutoConfirmation` mechanism (45s delay state machine). <!-- id: 18 -->
- [ ] T020: Integrate `AutoConfirmation` with `ToolExecutor` (execute if no cancel). <!-- id: 19 -->
- [ ] T021: Implement "Conciseness" logic (truncate/rewrite messages based on channel config). <!-- id: 20 -->
- [ ] T022: Final End-to-End verification of all 3 channels. <!-- id: 21 -->

**Prompt**: [WP05-channel-logic.md](tasks/WP05-channel-logic.md)
