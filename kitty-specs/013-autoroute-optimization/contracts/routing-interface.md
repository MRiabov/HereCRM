# Routing Interface Definition

## Service Protocol

The system will use a Strategy pattern for routing.

```python
class RoutingSolution(BaseModel):
    routes: List[Route]
    unassigned_jobs: List[Job]
    total_distance_meters: float
    total_duration_seconds: float

class Route(BaseModel):
    employee_id: int
    jobs: List[Job]  # In ordered sequence
    start_time: datetime
    end_time: datetime
    distance_meters: float

class RoutingService(Protocol):
    async def optimize_schedule(
        self, 
        jobs: List[Job], 
        employees: List[User], 
        date: datetime.date
    ) -> RoutingSolution:
        """
        Calculate optimal routes.
        """
        ...
```

## Internal Command: `autoroute`

**Invocation**:
`autoroute [date_string?]`

**Output (Preview)**:

```text
Optimization Results for 2026-01-22:

Employee: Bob
  09:00 - 10:00: Fix Sink (Customer A) [1.2km]
  10:15 - 11:15: Install Light (Customer B) [3.4km]

Employee: Alice
  09:00 - 12:00: Rewiring (Customer C) [0.5km]

Unassigned Jobs: 1
  - Job #123 (No availability match)

Total Travel: 5.1 km
Fuel Saved: ~0.5 gallons

[Confirm] / [Cancel]
```

## OpenRouteService VRP Payload (Reference)

```json
{
  "jobs": [
    {
      "id": 1,
      "location": [lng, lat],
      "service": 3600, # duration sec
      "time_windows": [[start_epoch, end_epoch]]
    }
  ],
  "vehicles": [
    {
      "id": 101,
      "profile": "driving-car",
      "start": [lng, lat],
      "end": [lng, lat] # Same as start (return to depot)
    }
  ]
}
```
