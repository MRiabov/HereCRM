import asyncio
from typing import Callable, Dict, List, Any, Awaitable, Union
import logging

# Event Names
JOB_CREATED = "JOB_CREATED"
JOB_SCHEDULED = "JOB_SCHEDULED"
JOB_UPDATED = "JOB_UPDATED"
JOB_BOOKED = "JOB_BOOKED"
JOB_COMPLETED = "JOB_COMPLETED"
JOB_CANCELLED = "JOB_CANCELLED"
JOB_ASSIGNED = "JOB_ASSIGNED"
JOB_UNASSIGNED = "JOB_UNASSIGNED"
CONTACT_EVENT = "CONTACT_EVENT"

logger = logging.getLogger(__name__)

class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[Any], Union[None, Awaitable[None]]]]] = {}

    def subscribe(self, event_name: str, callback: Callable[[Any], Union[None, Awaitable[None]]]):
        """Subscribe a callback to an event."""
        if event_name not in self._subscribers:
            self._subscribers[event_name] = []
        self._subscribers[event_name].append(callback)
        logger.debug(f"Subscribed to {event_name}")

    def on(self, event_name: str):
        """Decorator to subscribe a function to an event."""
        def decorator(func):
            self.subscribe(event_name, func)
            return func
        return decorator

    async def emit(self, event_name: str, data: Any = None):
        """Emit an event to all subscribers."""
        if event_name in self._subscribers:
            logger.debug(f"Emitting {event_name} with data: {data}")
            coroutines = []
            for callback in self._subscribers[event_name]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        coroutines.append(callback(data))
                    else:
                        callback(data)
                except Exception as e:
                    logger.error(f"Error in event handler for {event_name}: {e}", exc_info=True)

            if coroutines:
                results = await asyncio.gather(*coroutines, return_exceptions=True)
                for result in results:
                    if isinstance(result, Exception):
                        logger.error(f"Error in event handler for {event_name}: {result}", exc_info=True)
        else:
            logger.debug(f"No subscribers for {event_name}")

# Global EventBus instance
event_bus = EventBus()
