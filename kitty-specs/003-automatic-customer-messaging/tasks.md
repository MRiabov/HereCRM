# Tasks: 003 Automatic Customer Messaging

## Setup

- [ ] Unify configuration for WhatsApp/SMS @[WP01-foundation] <!-- id: 0 -->

## Foundational

- [ ] WP01: Scaffolding & Core Models @[WP01-foundation] <!-- id: 1 -->
  - [ ] T001: Create MessageLog model <!-- id: 2 -->
  - [ ] T002: Create EventBus service <!-- id: 3 -->
  - [ ] T003: Define Event classes <!-- id: 4 -->

## User Stories

- [ ] WP02: Messaging Service Infrastructure @[WP02-messaging-service] <!-- id: 5 -->
  - [ ] T004: Create MessagingService class <!-- id: 6 -->
  - [ ] T005: Implement send_message logic <!-- id: 7 -->
  - [ ] T006: Implement async queue consumer <!-- id: 8 -->
  - [ ] T007: Register MessagingService as listener <!-- id: 9 -->

- [ ] WP03: Job Lifecycle Events @[WP03-job-lifecycle] <!-- id: 10 -->
  - [ ] T008: Emit JobBookedEvent from Job creation <!-- id: 11 -->
  - [ ] T009: Emit JobScheduledEvent from Job scheduling <!-- id: 12 -->
  - [ ] T010: Implement handlers in MessagingService <!-- id: 13 -->

- [ ] WP04: Manual & Scheduled Triggers @[WP04-triggers] <!-- id: 14 -->
  - [ ] T011: Implement "On My Way" trigger <!-- id: 15 -->
  - [ ] T012: Implement Daily Schedule runner <!-- id: 16 -->
