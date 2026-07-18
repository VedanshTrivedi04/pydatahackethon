"""
Internal Event Bus.

A lightweight publish/subscribe event bus for decoupling domain logic.
Allows components (like JobService) to emit events without needing to know
who is listening (e.g., notification service, audit logs).

Note: This is an in-memory async event bus designed for the FastAPI process.
In a fully distributed environment, this could be backed by Redis Pub/Sub.
"""

import asyncio
import json
from typing import Callable, Awaitable, Any

from redis.asyncio import Redis

from engine.config.settings import get_settings
from engine.core.events.types import SystemEvent, EventType
from engine.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Type for event handler callbacks
EventHandler = Callable[[SystemEvent], Awaitable[None]]


class EventBus:
    """
    Singleton event bus backed by Redis Pub/Sub for distributed broadcasting.
    """
    _instance = None
    
    def __new__(cls) -> "EventBus":
        if cls._instance is None:
            cls._instance = super(EventBus, cls).__new__(cls)
            cls._instance._subscribers = {}
            cls._instance._redis = None
            cls._instance._listener_task = None
        return cls._instance
        
    def __init__(self) -> None:
        if not hasattr(self, "_subscribers"):
            self._subscribers: dict[EventType, list[EventHandler]] = {}
            self._redis = None
            self._listener_task = None

    async def connect(self) -> None:
        """Connect to Redis and start the listener background task."""
        if self._redis is None:
            self._redis = Redis.from_url(settings.redis.url, decode_responses=True)
            self._listener_task = asyncio.create_task(self._listen())
            logger.info("event_bus.connected", url=settings.redis.url)

    async def disconnect(self) -> None:
        """Close Redis connection and cancel listener."""
        if self._listener_task:
            self._listener_task.cancel()
        if self._redis:
            await self._redis.aclose()
            self._redis = None
            logger.info("event_bus.disconnected")

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """Register a new async handler for a specific event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        logger.debug("event_bus.subscribed", event_type=event_type, handler=handler.__name__)

    async def emit(self, event: SystemEvent) -> None:
        """
        Emit an event to Redis so all workers/API instances receive it.
        """
        if not self._redis:
            # Fallback for tests if not connected
            await self._redis_fallback_emit(event)
            return

        logger.info(
            "event_bus.emitted",
            event_type=event.type,
            event_id=event.id,
            tenant_id=event.tenant_id
        )
        
        # Publish to Redis channel "shipfaster.events"
        payload = event.model_dump_json()
        await self._redis.publish("shipfaster.events", payload)

    async def _redis_fallback_emit(self, event: SystemEvent) -> None:
        """Local emit if Redis isn't connected (e.g. unit tests)."""
        handlers = self._subscribers.get(event.type, [])
        for handler in handlers:
            asyncio.create_task(self._safe_execute(handler, event))

    async def _listen(self) -> None:
        """Background task that listens to Redis Pub/Sub."""
        if not self._redis:
            return
            
        pubsub = self._redis.pubsub()
        await pubsub.subscribe("shipfaster.events")
        
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        event = SystemEvent.model_validate(data)
                        
                        handlers = self._subscribers.get(event.type, [])
                        for handler in handlers:
                            asyncio.create_task(self._safe_execute(handler, event))
                    except Exception as e:
                        logger.error("event_bus.parse_error", error=str(e))
        except asyncio.CancelledError:
            await pubsub.unsubscribe("shipfaster.events")
            raise
        except Exception as e:
            logger.error("event_bus.listen_error", error=str(e))

    async def _safe_execute(self, handler: EventHandler, event: SystemEvent) -> None:
        """Execute a handler and catch any exceptions."""
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
