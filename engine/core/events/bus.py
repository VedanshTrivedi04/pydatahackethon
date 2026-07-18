"""
Internal Event Bus.

A lightweight publish/subscribe event bus for decoupling domain logic.
Allows components (like JobService) to emit events without needing to know
who is listening (e.g., notification service, audit logs).

Note: This is an in-memory async event bus designed for the FastAPI process.
In a fully distributed environment, this could be backed by Redis Pub/Sub.
"""

import asyncio
from typing import Callable, Awaitable, Any

from engine.core.events.types import SystemEvent, EventType
from engine.utils.logging import get_logger

logger = get_logger(__name__)

# Type for event handler callbacks
EventHandler = Callable[[SystemEvent], Awaitable[None]]


class EventBus:
    """
    Singleton event bus for internal pub/sub.
    """
    _instance = None
    
    def __new__(cls) -> "EventBus":
        if cls._instance is None:
            cls._instance = super(EventBus, cls).__new__(cls)
            cls._instance._subscribers = {}
        return cls._instance
        
    def __init__(self) -> None:
        # __init__ might be called multiple times due to singleton pattern,
        # but _subscribers is initialized in __new__
        if not hasattr(self, "_subscribers"):
            self._subscribers: dict[EventType, list[EventHandler]] = {}

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """Register a new async handler for a specific event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        logger.debug("event_bus.subscribed", event_type=event_type, handler=handler.__name__)

    async def emit(self, event: SystemEvent) -> None:
        """
        Emit an event to all registered subscribers.
        Subscribers are executed asynchronously in the background.
        """
        logger.info(
            "event_bus.emitted",
            event_type=event.type,
            event_id=event.id,
            tenant_id=event.tenant_id
        )
        
        handlers = self._subscribers.get(event.type, [])
        for handler in handlers:
            # Fire and forget
            asyncio.create_task(self._safe_execute(handler, event))

    async def _safe_execute(self, handler: EventHandler, event: SystemEvent) -> None:
        """Execute a handler and catch any exceptions so one bad handler doesn't break the bus."""
        try:
            await handler(event)
        except Exception as e:
            logger.error(
                "event_bus.handler_failed",
                event_type=event.type,
                handler=handler.__name__,
                error=str(e),
                exc_info=True
            )

# Global singleton instance
event_bus = EventBus()
