"""Domain services for agent coordination."""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone

from .entities import AgentProfile, AgentMessage, AgentStatus

logger = logging.getLogger(__name__)

class AgentCoordinator:
    """Service for coordinating multiple agents."""
    
    def __init__(self):
        self._agents: Dict[str, AgentProfile] = {}
        self._message_queue: List[AgentMessage] = []
        
    def register_agent(self, agent: AgentProfile) -> None:
        """Register a new agent."""
        self._agents[agent.id] = agent
        logger.info(f"Registered agent: {agent.name} ({agent.id})")
        
    def update_status(self, agent_id: str, status: AgentStatus) -> None:
        """Update agent status."""
        if agent_id in self._agents:
            self._agents[agent_id].status = status
            self._agents[agent_id].last_heartbeat = datetime.now(timezone.utc)
            
    def get_agent(self, agent_id: str) -> Optional[AgentProfile]:
        """Get agent profile."""
        return self._agents.get(agent_id)
        
    def get_active_agents(self) -> List[AgentProfile]:
        """Get list of active agents."""
        # Simple timeout check could be added here
        return [a for a in self._agents.values() if a.status != AgentStatus.OFFLINE]
        
    async def send_message(self, message: AgentMessage) -> None:
        """Send a message to an agent."""
        self._message_queue.append(message)
        logger.info(f"Message sent from {message.sender_id} to {message.recipient_id}: {message.message_type}")
        # In a real system, this would push to a queue or DB
        
    def get_messages(self, recipient_id: str) -> List[AgentMessage]:
        """Get messages for a recipient."""
        messages = [
            m for m in self._message_queue 
            if m.recipient_id == recipient_id or m.recipient_id == "all"
        ]
        # Clear retrieved messages? Or keep history?
        # For now, keep them.
        return messages
