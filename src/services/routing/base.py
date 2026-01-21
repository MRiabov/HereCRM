from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from src.models import Job, User

class RoutingException(Exception):
    """Raised when routing calculation fails."""
    pass

@dataclass
class RoutingStep:
    """
    Represents a specific visit in a route.
    """
    job: Job
    arrival_time: Optional[datetime] = None
    departure_time: Optional[datetime] = None

@dataclass
class RoutingSolution:
    """
    Represents the output of a routing optimization.
    """
    routes: Dict[int, List[RoutingStep]]
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
    
    def validate_locations(self, locations: List[Any]):
        """
        Optional validation of locations.
        """
        pass
