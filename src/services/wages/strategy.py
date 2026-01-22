from typing import Protocol, runtime_checkable, Dict, Any
from src.models import WageConfiguration

@runtime_checkable
class WageStrategy(Protocol):
    """Protocol for wage calculation strategies."""
    
    def calculate(self, config: WageConfiguration, context: Dict[str, Any]) -> float:
        """Calculate the wage based on configuration and context."""
        ...
