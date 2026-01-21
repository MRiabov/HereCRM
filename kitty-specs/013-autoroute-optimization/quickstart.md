# Quickstart: Autoroute Optimization

## Prerequisites

1. **Environment Variables**:
    - `ORS_API_KEY`: Required for production mode.
    - `ROUTING_PROVIDER`: Set to `mock` for local dev (default), `ors` for live.

2. **Dependencies**:
    - `openrouteservice` (Python client) or `httpx` for direct API calls.

## How to Test

1. **Set up Data**:
    - Create 2 Employees with `default_start_lat/lng`.
    - Create 3-5 Jobs for "Today" (unassigned).
    - Ensure Customers have `CustomerAvailability` entries for today.

2. **Run Optimization**:

    ```bash
    # In the app shell
    autoroute today
    ```

3. **Verify Mock**:
    - Expect logic to simply assign nearest job to employee, then next nearest from that job.
    - Result should appear instantly (<1s).

4. **Confirm**:
    - Type `Confirm` at the prompt.
    - Check `Job` table: `employee_id` and `scheduled_at` should be populated.

## Troubleshooting

- **"No valid start location"**: Ensure Employee has defaults set or specify in command (TBD if supported).
- **"ORS 403 Forbidden"**: Check API Key.
