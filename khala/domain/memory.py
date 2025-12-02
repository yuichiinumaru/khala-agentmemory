from dataclasses import dataclass
from datetime import datetime

@dataclass
class Memory:
    """
    Represents a memory in the agent's knowledge base.
    """
    id: str
    content: str
    created_at: datetime
    updated_at: datetime
    importance: float
