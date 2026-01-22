# Implementation Tasks: Ad Automation & Integrations

**Spec**: [015-ad-automation-integrations](spec.md) | **Status**: Planned

## Overview

This feature adds an integration layer for inbound lead ingestion and outbound event reporting (Webhooks, Meta CAPI). This enables automation with tools like Zapier and Facebook Ads.

## Work Packages

### WP01: Foundation & Data Model

- **Goal**: Establish the database schema and core services for managing integration configurations.
- **Priority**: High (Blocker)
- **Tests**: Unit tests for Model and Repository.
- **Subtasks**:
  - [x] T001: Create alembic migration for `integration_configs` table.
  - [x] T002: Implement `IntegrationConfig` SQLAlchemy model.
  - [x] T003: Create `IntegrationRepository` with CRUD and Key lookup.
  - [x] T004: Implement `IntegrationService` with API Key generation and hashing utils.
  - [x] T005: Add unit tests for Data Model and Repository.

### WP02: API Implementation

- **Goal**: Expose public endpoints for data ingestion and integration provisioning.
- **Priority**: High
- **Dependencies**: WP01
- **Tests**: Integration tests for all endpoints.
- **Subtasks**:
  - [x] T006: Implement `ApiKeyAuth` dependency for secure API access.
  - [x] T007: Implement `Signer` utility for URL signature verification.
  - [x] T008: Implement `POST /provision` endpoint for saving configs.
  - [x] T009: Implement `POST /leads` endpoint (Lead ingestion).
  - [x] T010: Implement `POST /requests` endpoint (Service Request ingestion).
  - [x] T011: Add integration tests for API endpoints.

### WP03: Webhook Dispatcher

- **Goal**: Build the generic outbound webhook system triggered by business events.
- **Priority**: Medium
- **Dependencies**: WP01, WP02
- **Tests**: Unit tests for dispatcher (mocked HTTP).
- **Subtasks**:
  - [x] T012: Verify and hook into `job.booked` event in `events.py`.
  - [x] T013: Create `IntegrationEventHandler` framework.
  - [x] T014: Implement generic Webhook dispatch logic (Signature, HTTP POST).
  - [x] T015: Add unit tests for Webhook dispatching.

### WP04: Meta CAPI Integration

- **Goal**: Implement specific logic for Meta Conversions API reporting.
- **Priority**: Medium
- **Dependencies**: WP03
- **Tests**: Integration tests (mocked Meta API).
- **Subtasks**:
  - [ ] **T016**: Implement PII normalization and hashing (SHA-256) utils.
  - [ ] **T017**: Implement `MetaCapiClient` for Facebook Graph API interactions.
  - [ ] **T018**: Integrate CAPI dispatch into `IntegrationEventHandler`.
  - [ ] **T019**: Add tests for Meta CAPI data mapping and transmission.
