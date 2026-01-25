# Implementation Plan: Advanced Search

*Path: .kittify/missions/software-dev/templates/plan-template.md*

**Branch**: `005-unified-search` | **Date**: 2026-01-15 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/005-unified-search/spec.md`

## Summary

Implement a centralized "Advanced Search" feature driven by a unified `SearchService`. This service will interpret natural language queries (via LLM) to search Customers, Jobs, and Requests with support for:

- Flexible text matching (Name, Phone, Description).
- Date range filtering (e.g., "created last week").
- Proximity search (using OpenStreetMap/Nominatim).
- Detailed vs. Concise output formatting.
- **API Exposure**: Global Search endpoint for PWA.

Technically, this refactors existing scattered search logic from `ToolExecutor` into a dedicated domain service and enhances `LLMClient` system instructions for better parameter extraction.

## Technical Context

**Language/Version**: Python 3.12+ (existing project standard)
**Primary Dependencies**:

- `sqlalchemy` (AsyncSession) for DB access.
- `httpx` for Geocoding API.
- `openai` (async) for LLM interactions.
- `pydantic` for Tool definitions.
**Storage**: SQLite (via `aiosqlite` per existing config).
**Testing**: `pytest` + `pytest-asyncio`.
**Target Platform**: Linux server (existing).
**Performance Goals**: <3s response time for standard queries.
**Constraints**:
- Respect Nominatim API rate limits (1 req/sec).
- WhatsApp message limits (requires pagination/truncation strategy).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*
[Skipped: No constitution file found]

## Project Structure

### Documentation (this feature)

```
kitty-specs/005-unified-search/
├── plan.md              # This file
├── research.md          # Decisions & Analysis
├── data-model.md        # Schema definitions
└── tasks.md             # Work breakdown
```

### Source Code (repository root)

```
src/
├── services/
│   ├── search_service.py  # [NEW] Orchestrates repositories + Geocoding + Formatting
│   └── geocoding.py       # [KEEP] Existing Geocoding logic
├── uimodels.py            # [MODIFY] Update SearchTool with 'detailed' flag
├── tool_executor.py       # [MODIFY] Remove search logic, delegate to SearchService
├── repositories.py        # [KEEP] Support for PipelineStage and LineItems already merged
└── llm_client.py          # [MODIFY] Update prompts for better entity detection (inc. Services)
```

## Proposed Changes

### 1. New Service: `SearchService` (`src/services/search_service.py`)

- **Move Logic**: Extract all search orchestration from `ToolExecutor._execute_search`.
- **Dependencies**: Inject `CustomerRepository`, `JobRepository`, `RequestRepository`, `ServiceRepository`, `GeocodingService`.
- **Responsibilities**:
  - Handle date parsing (string -> datetime).
  - Resolve addresses to coordinates (using `GeocodingService`).
  - Dispatch queries to appropriate repositories.
  - **Pipeline Support**: Filter Customers by `pipeline_stage`.
  - **Service Catalog**: Support searching for Services.
  - **Service-based Filtering**: Find Customers or Jobs based on services performed (join via Line Items).
  - **Pagination/Truncation**: Implement a robust strategy (e.g., hard limit of 10 items).
  - **Formatting**: Implement `_format_customer`, `_format_job`, `_format_service` methods to handle "Detailed" vs "Concise" views.
  - **Detailed View**: For Jobs, include full Line Item breakdown (from Feature 004). For Customers, include full details/notes and pipeline stage history (if applicable).

### 2. Refactor: `ToolExecutor` (`src/tool_executor.py`)

- **Inject**: Add `search_service` to `__init__`.
- **Simplify**: `_execute_search` becomes a thin wrapper asking `search_service` for a result string.

### 3. Update: `SearchTool` (`src/uimodels.py`)

- Add `detailed: bool = False` field.

### 4. Refactor: Repositories (`src/repositories.py`)

- **`CustomerRepository`**: Existing `search()` supports flexible filtering including `pipeline_stage`. Needs update to support joining `Job` + `LineItem` for service-based filtering.
- **`JobRepository`**:
  - **[KEEP]** Already implements basic search and `line_items` loading. Needs update to support filtering by `service_id` or line item description.
- **`RequestRepository`**:
  - **[NOTE]** Proximity search cannot be supported as `Request` entity lacks location data.
- **`ServiceRepository`**:
  - **[NEW SEARCH]** Implement `search()` method to support text matching on service names for Unified Search.

### 5. API Exposure

- Expose Global Search endpoints for PWA as defined in OpenAPI.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| New Service Layer | Search logic is becoming complex (Geo + Text + Date) | Keeping in `ToolExecutor` (God Class anti-pattern) makes testing and maintenance hard. |
| Python-side Geo-filtering | database is SQLite (no PostGIS) | Adding SpatiaLite extension is too complex for current deployment. |

## Verification Plan

### Automated Tests

- **Job Proximity**: Create jobs at specific lat/long, verify `JobRepository.search` filters correctly by radius.
- **Detailed View**: Verify `SearchService` returns expanded fields when `detailed=True`.
- **Pagination**: Create 15 items, verify search returns <= 10.
- **Request Search**: Verify text search works (and proximity args are safely ignored).

### Manual Verification

- `spec-kitty agent run -- "Find jobs near Dublin"` -> check output.
- `spec-kitty agent run -- "Show customers detailed"` -> check output.
