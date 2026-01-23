# Implementation Plan: Job Documents & Attachments

*Path: kitty-specs/022-job-documents-attachments/plan.md*

**Branch**: `022-job-documents-attachments` | **Date**: 2026-01-22 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/022-job-documents-attachments/spec.md`

## Summary

This feature adds the ability for customers and business owners to upload, store, and retrieve documents (images, PDFs) via WhatsApp and Email, as well as attach external cloud links. It introduces a Secure Storage Service (using Backblaze B2 via boto3) and updates the messaging logic to auto-associate incoming media with active jobs.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: FastAPI, boto3 (for S3/Backblaze), Twilio (signature validation), Pydantic
**Storage**:

* **Database**: SQLite (via SQLAlchemy) for metadata (`Document` model).
* **Object Storage**: Backblaze B2 (S3-compatible) for file content.
* **Architecture Note**: `Document` serves as the unified registry for all files. `Quote` and `Invoice` models will be refactored to remove direct file columns (`blob_url`, `s3_key`) and instead link to a `Document` record. This allows a single query to retrieve all collateral for a job (User uploads + System generated files).
**Testing**: pytest (integration tests for webhook flow and storage service), plus migration tests.
**Target Platform**: Linux server.
**Project Type**: Web Application (Backend).
**Constraints**:
* Secure Time-Limited (Presigned) URLs for retrieval.
* Tenant isolation (Business ID enforcement).
* Async I/O for file operations.
* **Migration**: Must migrate existing `Quote.blob_url` and `Invoice.s3_key` data to new `Document` rows.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

* **Complexity**: 0/1 Allowed. This feature adds a new subsystem (Storage) but keeps it modular (`StorageService`). No microservices.
* **Tech Stack**: Standard stack (Python/FastAPI/SQLAlchemy). No new languages.
* **Security**: Enforces Presigned URLs (no public buckets) and Tenant Isolation.

## Project Structure

### Documentation (this feature)

```
kitty-specs/022-job-documents-attachments/
├── plan.md              # This file
├── research.md          # Storage & Integration decisions
├── data-model.md        # Document entity definition
└── contracts/           # Internal Service Interfaces (no public API changes)
```

### Source Code (repository root)

```
src/
├── models/
│   └── __init__.py      # Add Document model here
├── services/
│   ├── storage_service.py # NEW: Wrapper around boto3
│   ├── document_service.py # NEW: Logic for association and storage
│   ├── whatsapp_service.py # UPDATE: Handle media_url
│   └── data_management.py # REFACTOR: Maybe share storage logic?
└── api/
    └── routes.py        # UPDATE: Extract media from payloads
```

## Complexity Tracking

No violations.
