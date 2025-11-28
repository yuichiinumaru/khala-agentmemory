"""
Live Protocol Service for Multi-Agent Coordination.

This module handles SurrealDB LIVE queries to enable real-time coordination
between agents.
"""

import asyncio
import logging
from typing import Dict, Any, Callable, List
from ...infrastructure.surrealdb.client import SurrealDBClient

logger = logging.getLogger(__name__)

class LiveProtocolService:
    """
    Manages real-time subscriptions and event dispatching for the Multi-Agent Protocol.
    """

    def __init__(self, db_client: SurrealDBClient):
        self.db_client = db_client
        self.handlers: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}
        self.active_subscriptions: Dict[str, asyncio.Task] = {}
        self.is_running = False

    async def start(self):
        """Start the protocol service."""
        self.is_running = True
        logger.info("LiveProtocolService started.")
        # Start default subscriptions
        self.active_subscriptions['memory'] = asyncio.create_task(self._monitor_table('memory'))

    async def stop(self):
        """Stop the protocol service."""
        self.is_running = False
        for task in self.active_subscriptions.values():
            task.cancel()
        self.active_subscriptions.clear()
        logger.info("LiveProtocolService stopped.")

    def register_handler(self, event_type: str, handler: Callable[[Dict[str, Any]], None]):
        """Register a callback for a specific event type."""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
        logger.debug(f"Registered handler for {event_type}")

    async def _monitor_table(self, table_name: str):
        """Monitor a specific table for changes."""
        logger.info(f"Starting LIVE monitor on table: {table_name}")
        try:
            async for event in self.db_client.listen_live(table_name):
                if not self.is_running:
                    break

                await self._process_event(table_name, event)
        except asyncio.CancelledError:
            logger.info(f"Stopped LIVE monitor on {table_name}")
        except Exception as e:
            logger.error(f"Error monitoring {table_name}: {e}")
            # Restart monitor after delay if running
            if self.is_running:
                await asyncio.sleep(5)
                self.active_subscriptions[table_name] = asyncio.create_task(self._monitor_table(table_name))

    async def _process_event(self, table: str, event: Dict[str, Any]):
        """Process an incoming database event."""
        action = event.get("action")
        result = event.get("result")

        if not action or not result:
            return

        # Map DB events to Protocol Events
        protocol_event_type = None

        if table == "memory" and action == "CREATE":
            protocol_event_type = "MEMORY_CREATED"
        elif table == "debate" and action == "CREATE": # Assuming debate table exists or will exist
            protocol_event_type = "DEBATE_REQUEST"

        if protocol_event_type:
             await self._dispatch_event(protocol_event_type, result)

    async def _dispatch_event(self, event_type: str, data: Dict[str, Any]):
        """Dispatch event to registered handlers."""
        if event_type in self.handlers:
            logger.info(f"Dispatching {event_type} to {len(self.handlers[event_type])} handlers")
            for handler in self.handlers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(data)
                    else:
                        handler(data)
                except Exception as e:
                    logger.error(f"Error in event handler for {event_type}: {e}")
