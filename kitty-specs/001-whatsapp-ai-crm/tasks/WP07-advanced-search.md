# Implementation Tasks: Advanced Search & Filtering (WP07)

**Feature**: WhatsApp AI CRM
**Status**: Implemented
**Priority**: High - Core Feature
**Test**: `pytest tests/test_search_features.py`

## Description

Enhance the search capabilities beyond simple text matching to include structured filtering by date, entity type, status, and creation time. This enables powerful queries like "jobs today", "leads added last week", and "pending requests".

## Tasks

- [x] **T026**: Update `SearchTool` model to include `entity_type`, `query_type`, `min_date`, `max_date`, `status`.
- [x] **T027**: Enhance `CustomerRepository.search` to support `created_at` filtering, `lead` detection (0 jobs), and cross-referencing jobs (`scheduled`).
- [x] **T028**: Enhance `JobRepository.search` to support `scheduled_at` date ranges and status filtering.
- [x] **T029**: Enhance `RequestRepository.search` to support `created_at` and status filtering.
- [x] **T030**: Update `ToolExecutor` to parse inputs into structured `SearchTool` calls (handling date parsing logic if not fully handled by LLM).
- [x] **T031**: Create comprehensive `test_search_features.py` suite covering 15+ scenarios.
