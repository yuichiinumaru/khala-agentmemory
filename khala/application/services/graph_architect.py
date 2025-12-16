import logging
import json
from typing import List, Dict, Any
from khala.infrastructure.gemini.client import GeminiClient
from khala.infrastructure.gemini.models import GEMINI_REASONING
from khala.domain.prompt.utils import System, User

logger = logging.getLogger(__name__)

class GraphArchitect:
    """Agent responsible for evolving the knowledge graph structure (Strategy 171)."""

    def __init__(self, client: GeminiClient):
        self.client = client

    async def propose_connections(self, orphan_content: str, candidates: List[Dict[str, Any]]) -> List[str]:
        """
        Analyze an orphan node against candidates and propose links.
        Returns a list of candidate IDs to link to.
        """
        if not candidates:
            return []

        candidate_summary = "\n".join([f"- ID: {c['id']}, Content: {c.get('content', '')[:100]}..." for c in candidates])

        prompt = (
            System("You are a Knowledge Graph Architect. Your goal is to connect orphaned nodes to the graph.") /
            User(f"""
            Orphan Node Content:
            {orphan_content}

            Candidate Nodes:
            {candidate_summary}

            Identify which candidates (if any) are semantically related to the orphan node and should be linked.
            Output a JSON list of IDs: ["id1", "id2"]. If none, output [].
            """)
        )

        try:
            response = await self.client.generate_text(
                str(prompt),
                model_id=GEMINI_REASONING
            )
            content = response.get("content", "[]")
            # Parse JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            links = json.loads(content)
            if isinstance(links, list):
                return links
            return []

        except Exception as e:
            logger.error(f"GraphArchitect failed to propose links: {e}")
            return []
