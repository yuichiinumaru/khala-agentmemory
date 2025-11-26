"""Context-aware tool selection service."""

import logging
import json
from typing import List, Dict, Any
from khala.infrastructure.gemini.client import GeminiClient

logger = logging.getLogger(__name__)

class ToolSelector:
    """Selects the best tools for a task based on context."""
    
    def __init__(self, gemini_client: GeminiClient):
        self.gemini_client = gemini_client
        
    async def select_tools(
        self, 
        task: str, 
        context: str, 
        available_tools: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Select relevant tools for the task.
        Returns a list of tool names.
        """
        if not available_tools:
            return []
            
        tools_desc = "\n".join([f"- {t['name']}: {t['description']}" for t in available_tools])
        
        prompt = f"""
        Task: {task}
        
        Context:
        {context}
        
        Available Tools:
        {tools_desc}
        
        Select the tools from the list that are necessary to complete the task given the context.
        Return ONLY a JSON list of tool names. Example: ["tool_a", "tool_b"]
        """
        
        try:
            response = await self.gemini_client.generate_text(
                prompt,
                model_id="gemini-2.0-flash",
                temperature=0.0
            )
            
            content = response["content"]
            # Clean up markdown code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
                
            selected_tools = json.loads(content.strip())
            if isinstance(selected_tools, list):
                return selected_tools
            return []
            
        except Exception as e:
            logger.error(f"Error selecting tools: {e}")
            return []
