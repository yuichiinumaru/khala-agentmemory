"""Tool wrapper for executing other agents as tools."""

from typing import Any, Dict, List, Optional, Union
import logging
from dataclasses import dataclass

try:
    from agno.agent import Agent as AgnoAgent
    from agno.tools import Tool
except ImportError:
    # Fallback types for type hinting
    AgnoAgent = Any
    Tool = Any

from ..khala_agent import KHALAAgent

logger = logging.getLogger(__name__)

class AgentToolWrapper:
    """Wrapper to expose an Agent as a callable Tool."""

    def __init__(
        self,
        agent: Union[KHALAAgent, AgnoAgent],
        name: Optional[str] = None,
        description: Optional[str] = None
    ):
        """Initialize the wrapper.

        Args:
            agent: The agent instance to wrap (KHALA or Agno Agent)
            name: Name of the tool (defaults to agent.name)
            description: Description of tool (defaults to agent.description)
        """
        self.agent = agent
        self.name = name or getattr(agent, "name", "AgentTool")
        self.description = description or getattr(agent, "description", "An agent accessible as a tool.")

    def run(self, query: str, **kwargs) -> str:
        """Execute the agent with a query.

        Args:
            query: The input query/prompt for the agent

        Returns:
            The agent's response as a string
        """
        try:
            # Handle KHALAAgent
            if isinstance(self.agent, KHALAAgent):
                # We need to run this async, but tools are often synchronous in some frameworks.
                # If running in async context, we might need a sync wrapper or use asyncio.run
                # Assuming this is called from an environment that can handle sync calls or we block.
                import asyncio

                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = None

                if loop and loop.is_running():
                     # We are in an async loop. If the caller expects a sync return, we have a problem.
                     # However, most modern agent frameworks support async tools.
                     # But if we must return str synchronously:
                     # This is tricky. Ideally the tool interface should be async.
                     # For now, let's assume we can return a coroutine if the caller supports it,
                     # or use a nesting strategy if possible (which is dangerous).

                     # Since KHALAAgent.process_message is async:
                     raise RuntimeError("Cannot call async KHALA agent from sync tool wrapper inside running loop. Please await wrapper.arun() instead.")
                else:
                    response = asyncio.run(self.agent.process_message(query, user_id="system_tool_call"))
                    return str(response.get("response", ""))

            # Handle Agno Agent
            elif hasattr(self.agent, "run"):
                # Agno agents usually have a .run() or .print_response() method
                # Check Agno documentation or inspection.
                # Assuming .run() returns a response object or string.
                response = self.agent.run(query)
                if hasattr(response, "content"):
                    return response.content
                return str(response)

            # Handle Agno Agent (alternative method)
            elif hasattr(self.agent, "print_response"):
                # This prints to stdout usually, not what we want for a tool.
                # Look for a generation method.
                # Trying .chat() or similar if available.
                return f"Agent {self.name} execution not fully supported in this wrapper version."

            else:
                return f"Unsupported agent type: {type(self.agent)}"

        except Exception as e:
            logger.error(f"Error executing agent tool {self.name}: {e}")
            return f"Error executing agent: {str(e)}"

    async def arun(self, query: str, **kwargs) -> str:
        """Async execution of the agent."""
        try:
             if isinstance(self.agent, KHALAAgent):
                 response = await self.agent.process_message(query, user_id="system_tool_call")
                 return str(response.get("response", ""))
             elif hasattr(self.agent, "arun"):
                 response = await self.agent.arun(query)
                 return str(response)
             else:
                 # Fallback to sync run in thread pool if needed, or just call sync
                 return self.run(query, **kwargs)
        except Exception as e:
             logger.error(f"Error executing agent tool {self.name}: {e}")
             return f"Error executing agent: {str(e)}"

    def to_tool(self) -> Any:
        """Convert to Agno/LangChain compatible tool object if needed."""
        # For Agno, a tool can be a function or a class with run method.
        # We can return self, as it has a run method.
        return self
