---
lane: "doing"
agent: "antigravity"
shell_pid: "284006"
---
# WP05: Employee Invitation Flow

## Goal

Implement a chat-based invitation flow where owners can invite new employees.

## Tasks

- [ ] **Data Model Implementation**: Create `Invitation` model and migration.
- [ ] **Context Implementation**: Implement foundational "Employee Management" context check.
- [ ] **Tool Development**: Implement `InviteUserTool` (restricted to Management context).
- [ ] **Join Logic**: Implement `JoinBusinessTool` (keyword responder) to process acceptance.
- [ ] **Messaging Integration**: Update `MessagingService` to handle outbound invitation messages.
- [ ] **Integration Tests**: Verify the full invite -> receive -> join flow.

## Acceptance Criteria

- Owner can say "Invite +123456789" and the system sends a message. The message should be parsed only in the employee management settings.
- The recipient can say "Join" and is added as an employee.
- Duplicate invites are handled.

## Activity Log

- 2026-01-22T19:43:05Z – antigravity – shell_pid=284006 – lane=doing – Started implementation via workflow command
