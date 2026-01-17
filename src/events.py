import asyncio
from typing import Callable, Dict, List, Any, Awaitable, Union, Optional
import logging

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

    async def emit(self, event_name: str, data: Any = None):
        """Emit an event to all subscribers."""
        if event_name in self._subscribers:
            logger.debug(f"Emitting {event_name} with data: {data}")
            for callback in self._subscribers[event_name]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(data)
                    else:
                        callback(data)
                except Exception as e:
                    logger.error(f"Error in event handler for {event_name}: {e}", exc_info=True)
        else:
            logger.debug(f"No subscribers for {event_name}")

# Global EventBus instance
event_bus = EventBus()
