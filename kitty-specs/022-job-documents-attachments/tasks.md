
# Work Packages: Job Documents & Attachments

**Feature**: 022-job-documents-attachments
**Status**: Planning

## Work Package 01: Storage Foundation & Models

**Goal**: Setup secure storage infrastructure and database models.
**Priority**: High
**Dependencies**: None

- [ ] T001: Add `Document` model and migration [P]
- [ ] T002: Add `boto3` dependency and config
- [ ] T003: Implement `StorageService` (upload, presign)
- [ ] T004: Test `StorageService` (mocked S3)

## Work Package 02: Document Service Core

**Goal**: Implement business logic for document management and association.
**Priority**: High
**Dependencies**: WP01

- [ ] T005: Implement `DocumentService` (create, get)
- [ ] T006: Implement `auto_associate_job` logic
- [ ] T007: Integration tests for DocumentService

## Work Package 03: Ingestion Pipelines (WhatsApp & Links)

**Goal**: Handle incoming media from WhatsApp/SMS and parse external links.
**Priority**: Medium
**Dependencies**: WP02

- [ ] T008: Implement Link Parsing Utility (Regex/Allowlist) [P]
- [ ] T009: Update Message Handler for Media (WhatsApp/Twilio)
- [ ] T010: Update Message Handler for Text Links
- [ ] T011: Integration tests for Ingestion

## Work Package 04: Retrieval Tools

**Goal**: Allow users to query and retrieve documents via chat.
**Priority**: Medium
**Dependencies**: WP02

- [ ] T012: Create `GetJobDocumentsTool` (or similar intent)
- [ ] T013: Format response with Presigned URLs
- [ ] T014: E2E tests for Retrieval flow

## Work Package 05: Email Integration

**Goal**: Process email attachments from Postmark.
**Priority**: Low
**Dependencies**: WP02

- [ ] T015: Implement/Update Postmark Webhook for Attachments
- [ ] T016: Extract and Process Inbound Email Attachments
