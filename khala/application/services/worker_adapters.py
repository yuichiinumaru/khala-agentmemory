"""Adapters for integrating Agno Tools into the Khala Planner.

Bridge between `khala.application.services.planning_service.Worker` and Agno framework components.
"""

import logging
import inspect
from typing import Any, Dict, Optional, Callable

from khala.application.services.planning_service import Worker

logger = logging.getLogger(__name__)

class AgnoToolWorker(Worker):
    """Adapter to treat an Agno Tool as a Khala Worker."""

    def __init__(self, tool_instance: Any):
        """
        Args:
            tool_instance: An instance of an Agno Tool.
                           Expected to have a `run` or `execute` method and a `description`.
        """
        self.tool = tool_instance
        self.name = getattr(tool_instance, "name", "Unnamed Agno Tool")

    async def hint(self) -> str:
        """Return the tool description."""
        # Try to get description from attribute or docstring
        desc = getattr(self.tool, "description", None)
        if not desc:
            desc = self.tool.__doc__
        if not desc:
            desc = f"Tool {self.name} with unknown capabilities."
        return f"{self.name}: {desc}"

    async def handle(self, param: str, ctx: Dict[str, Any]) -> Any:
        """Execute the tool with the provided parameter."""
        logger.info(f"Executing Agno Tool {self.name} with param: {param}")

        # Agno tools typically have a run method.
        # Check for 'arun' (async) first, then 'run' (sync).
        method = getattr(self.tool, "arun", None)
        is_async = True

        if not method:
            method = getattr(self.tool, "run", None)
            is_async = False

        if not method:
            # Maybe it's a callable itself?
            if callable(self.tool):
                method = self.tool
                is_async = inspect.iscoroutinefunction(method)
            else:
                raise ValueError(f"Tool {self.name} has no run/arun method and is not callable.")

        try:
            # Agno tools usually take a single string or **kwargs.
            # We assume single string param here as per parse_step logic.
            if is_async:
                return await method(param)
            else:
                return method(param)
        except Exception as e:
            logger.error(f"Error executing Agno tool {self.name}: {e}")
            return f"Error: {str(e)}"
