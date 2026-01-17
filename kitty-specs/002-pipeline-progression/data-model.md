# Data Model: Pipeline Progression

## Entities

### `PipelineStage` (Enum)

*New Enumeration*

| Value | Description |
|-------|-------------|
| `NOT_CONTACTED` | Default stage for new leads/customers with no jobs. |
| `CONTACTED` | Customer has been contacted but no jobs booked yet. |
| `CONVERTED_ONCE` | Customer has exactly one job. |
| `CONVERTED_RECURRENT` | Customer has more than one job. |
| `NOT_INTERESTED` | Explicitly marked as not interested. |
| `LOST` | Explicitly marked as lost. |

### `Customer` (Extended)

*Existing Model*

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `pipeline_stage` | `PipelineStage` | Yes | Defaults to `NOT_CONTACTED`. |

## State Transitions

| From | Event | To | Condition |
|------|-------|----|-----------|
| `NOT_CONTACTED` | `JOB_CREATED` | `CONVERTED_ONCE` | `job_count == 1` |
| `CONTACTED` | `JOB_CREATED` | `CONVERTED_ONCE` | `job_count == 1` |
| `CONVERTED_ONCE` | `JOB_CREATED` | `CONVERTED_RECURRENT` | `job_count > 1` |
| Any | User Command | `CONTACTED` | Manual interaction (or auto-detected msg) |
| Any | User Command | `NOT_INTERESTED` | Manual "mark as not interested" |
| Any | User Command | `LOST` | Manual "mark as lost" |

## Validation Rules

1. `pipeline_stage` must be a valid member of `PipelineStage` enum.
