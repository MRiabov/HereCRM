import asyncio
import logging
from typing import Type, Callable, List, Dict, Any

logger = logging.getLogger(__name__)

class EventBus:
    """
    A simple internal Event Bus for decoupling event producers from consumers.
    """
    def __init__(self):
        self._handlers: Dict[Type, List[Callable]] = {}

    def subscribe(self, event_type: Type, handler: Callable):
        """
        Subscribe a handler to an event type.
        Handlers are expected to be async functions.
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        if handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)
            logger.debug(f"Subscribed {handler.__name__} to {event_type.__name__}")

    async def emit(self, event: Any):
        """
        Emit an event to all subscribed handlers.
        """
        event_type = type(event)
        logger.debug(f"Emitting event: {event_type.__name__}")
        
        if event_type in self._handlers:
            handlers = self._handlers[event_type]
            # Execute handlers concurrently
            tasks = []
            for handler in handlers:
                if asyncio.iscoroutinefunction(handler):
                    tasks.append(handler(event))
                else:
                    # Support for sync handlers by wrapping them
                    loop = asyncio.get_running_loop()
                    tasks.append(loop.run_in_executor(None, handler, event))
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
                # Note: exceptions are caught but we might want to log them
                # For now, keeping it simple.

# Global singleton instance
event_bus = EventBus()
