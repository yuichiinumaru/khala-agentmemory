from typing import List, Dict, Any, Optional
import json
import logging
from khala.infrastructure.gemini.client import GeminiClient
from khala.domain.memory.entities import Memory

logger = logging.getLogger(__name__)

class ToolSelectionService:
    """
    Service for Context-Aware Tool Selection (Strategy 55).
    Dynamically recommends MCP tools based on current memory context.
    """

    # Registry of available tools (Could be dynamic in future)
    AVAILABLE_TOOLS = [
        {
            "name": "analyze_memories_parallel",
            "description": "Analyze multiple memories in parallel to extract insights, sentiment, and quality metrics.",
            "use_case": "Deep analysis of content, sentiment analysis, quality assurance."
        },
        {
            "name": "extract_entities_batch",
            "description": "Extract entities (people, places, concepts) from multiple texts in parallel.",
            "use_case": "Building knowledge graph, identifying key actors or objects."
        },
        {
            "name": "consolidate_memories_smart",
            "description": "Intelligently merge similar memories into a cohesive summary.",
            "use_case": "Cleaning up duplicate or fragmented information, summarization."
        },
        {
            "name": "verify_memories_comprehensive",
            "description": "Run multi-agent verification (fact-check, source-check) on memories.",
            "use_case": "Validating critical information, fact-checking, debate."
        },
        {
            "name": "search_memories",
            "description": "Search the memory database using text or vector similarity.",
            "use_case": "Retrieving information, answering questions."
        },
        {
            "name": "decompose_goal",
            "description": "Break down a high-level goal into actionable sub-tasks.",
            "use_case": "Planning, project management, complex task execution."
        },
        {
            "name": "test_hypothesis",
            "description": "Formulate and verify a theory against existing memories.",
            "use_case": "Investigation, research, validating assumptions."
        }
    ]

    def __init__(self, gemini_client: GeminiClient):
        self.gemini_client = gemini_client

    async def select_tools(
        self,
        query: str,
        recent_memories: List[Memory],
        max_tools: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Select the most relevant tools based on the user query and recent memory context.

        Args:
            query: The user's current request or query.
            recent_memories: List of recent interaction memories.
            max_tools: Maximum number of tools to recommend.

        Returns:
            List of selected tool definitions (name, reason).
        """
        # Prepare context summary
        context_summary = "\n".join([f"- {m.content[:100]}..." for m in recent_memories[:5]])

        tools_description = json.dumps(self.AVAILABLE_TOOLS, indent=2)

        prompt = f"""
        You are an intelligent agent orchestrator.
        Based on the User Query and Recent Context, select the best tools from the Available Tools list.

        User Query: {query}

        Recent Context:
        {context_summary}

        Available Tools:
        {tools_description}

        Select up to {max_tools} tools that are most likely to solve the user's problem.
        Return the result as a JSON list of objects:
        [
            {{"name": "tool_name", "reason": "Why this tool is needed"}}
        ]
        """

        try:
            response = await self.gemini_client.generate_text(
                prompt=prompt,
                model_id="gemini-2.5-flash", # Fast model is sufficient for selection
                temperature=0.1 # Low temperature for deterministic selection
            )

            content = response["content"]
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            selected_tools = json.loads(content.strip())

            # Validate tools against registry
            valid_names = {t["name"] for t in self.AVAILABLE_TOOLS}
            validated_selection = [
                t for t in selected_tools
                if t.get("name") in valid_names
            ]

            return validated_selection

        except Exception as e:
            logger.error(f"Tool selection failed: {e}")
            # Fallback: Return search tool if query seems like a question
            if "?" in query:
                 return [{"name": "search_memories", "reason": "Fallback: Question detected."}]
            return []

    def get_tool_definition(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get full definition of a tool by name."""
        for tool in self.AVAILABLE_TOOLS:
            if tool["name"] == tool_name:
                return tool
        return None
