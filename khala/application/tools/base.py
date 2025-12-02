from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type
from pydantic import BaseModel

class AgentTool(ABC):
    """
    Base class for Agent Tools.
    Standardized interface to call other agents or tools.
    """

    def __init__(
        self,
        name: str,
        description: str,
        args_schema: Optional[Type[BaseModel]] = None
    ):
        self.name = name
        self.description = description
        self.args_schema = args_schema

    @abstractmethod
    async def run(self, **kwargs) -> Any:
        """Execute the tool."""
        pass

    def validate_args(self, **kwargs) -> Dict[str, Any]:
        """Validate arguments against schema if present."""
        if self.args_schema:
            try:
                validated = self.args_schema(**kwargs)
                return validated.model_dump()
            except Exception as e:
                raise ValueError(f"Invalid arguments for tool {self.name}: {e}")
        return kwargs
