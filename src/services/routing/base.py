from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from src.models import Job, User

class RoutingException(Exception):
    """Raised when routing calculation fails."""
    pass

@dataclass
class RoutingSolution:
    """
    Represents the output of a routing optimization.
    """
    routes: Dict[int, List[Job]]
    unassigned_jobs: List[Job]
    metrics: Dict[str, Any] = field(default_factory=dict)

class RoutingServiceProvider(ABC):
    """
    Abstract base class for routing services.
    """
    
    @abstractmethod
    def calculate_routes(self, jobs: List[Job], employees: List[User]) -> RoutingSolution:
        """
        Calculate optimal routes for the given jobs and employees.
        
        Args:
            jobs: List of Job objects to be routed.
            employees: List of User objects (technicians) available for routing.
            
        Returns:
            RoutingSolution containing assigned routes and unassigned jobs.
        """
        pass

    @abstractmethod
    def get_eta_minutes(self, start_lat: float, start_lng: float, end_lat: float, end_lng: float) -> Optional[int]:
        """
        Calculate ETA in minutes between two points.
        """
        pass
    
    def validate_locations(self, locations: List[Any]):
        """
        Optional validation of locations.
        """
        pass
