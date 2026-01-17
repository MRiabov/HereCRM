# Data Model: Advanced Search

*Path: .kittify/missions/software-dev/templates/data-model-template.md*

**Feature**: Advanced Search
**Date**: 2026-01-15

## Domain Services

### `SearchService`

Central service for executing search queries.

- **Methods**:
  - `search(query: SearchTool, business_id: int) -> str`
    - Orchestrates calls to repositories.
    - Handles geocoding (via GeocodingService).
    - Formats output based on parameters (detailed/concise).
  - `_format_detailed(entity: Any) -> str`
  - `_format_concise(entity: Any) -> str`

## Entities

*No new Database Entities. Reusing `Customer`, `Job`, `Request`.*

## Value Objects / DTOs

### `SearchTool` (Pydantic Model - Updated)

Updated definition in `src/uimodels.py`:

```python
class SearchTool(BaseModel):
    query: str
    entity_type: Optional[str] # 'job', 'customer', 'request', 'lead', 'service'
    detailed: bool = False # [NEW]
    pipeline_stage: Optional[str] # [ALREADY MERGED FROM 002]
    service_query: Optional[str] # [NEW] Filter entities by service performed
    # ... existing fields ...
    # Support for date ranges:
    min_date: Optional[str] 
    max_date: Optional[str]
```
