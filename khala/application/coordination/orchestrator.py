"""
Multi-Agent Orchestrator.

Coordinates activities between external agents and internal subagents.
"""

import logging
from typing import Dict, Any
from .live_protocol import LiveProtocolService
from ...infrastructure.surrealdb.client import SurrealDBClient

logger = logging.getLogger(__name__)

class MultiAgentOrchestrator:
    """
    Orchestrates multi-agent interactions using the Live Protocol.
    """

    def __init__(self, db_client: SurrealDBClient):
        self.db_client = db_client
        self.live_protocol = LiveProtocolService(db_client)

        # Register core handlers
        self.live_protocol.register_handler("MEMORY_CREATED", self._handle_new_memory)
        self.live_protocol.register_handler("DEBATE_REQUEST", self._handle_debate_request)

    async def start(self):
        """Start the orchestrator and protocol service."""
        await self.live_protocol.start()
        logger.info("MultiAgentOrchestrator started")

    async def stop(self):
        """Stop the orchestrator."""
        await self.live_protocol.stop()
        logger.info("MultiAgentOrchestrator stopped")

    async def _handle_new_memory(self, memory_data: Dict[str, Any]):
        """Handle new memory creation event."""
        logger.info(f"Orchestrator received new memory: {memory_data.get('id')}")
        # Logic to trigger analysis or other agents could go here
        # e.g., if memory importance > 0.9, notify other agents

    async def _handle_debate_request(self, debate_data: Dict[str, Any]):
        """Handle debate requests."""
        logger.info(f"Orchestrator received debate request: {debate_data.get('id')}")
        # Logic to spin up debating subagents
