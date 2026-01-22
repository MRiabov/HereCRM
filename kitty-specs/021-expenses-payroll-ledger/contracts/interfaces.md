# Interfaces and Contracts

## Python Interfaces

### WageStrategy

```python
from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime

class WageStrategy(ABC):
    @abstractmethod
    def calculate_wage(
        self, 
        wage_config: 'WageConfiguration', 
        job: Optional['Job'] = None, 
        time_delta: Optional[float] = None, # Hours
        revenue: Optional[float] = None
    ) -> float:
        """
        Calculate the wage amount based on the strategy.
        - Commission: uses `revenue`
        - Hourly: uses `time_delta`
        - Daily: constant based on config
        """
        pass
```

## Tool Definitions (JSON Schema)

### StartJobTool

```json
{
  "name": "StartJobTool",
  "description": "Records the start time for a specific job.",
  "parameters": {
    "type": "object",
    "properties": {
      "job_id": {
        "type": "integer",
        "description": "The ID of the job to start."
      }
    },
    "required": ["job_id"]
  }
}
```

### AddExpenseTool

```json
{
  "name": "AddExpenseTool",
  "description": "Records a business expense.",
  "parameters": {
    "type": "object",
    "properties": {
      "amount": { "type": "number" },
      "description": { "type": "string" },
      "category": { "type": "string" },
      "job_id": { "type": "integer", "description": "Optional Job ID to link expense to." },
      "date": { "type": "string", "format": "date-time" }
    },
    "required": ["amount", "description"]
  }
}
```
