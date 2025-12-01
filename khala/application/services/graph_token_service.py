"""Graph Token Service (Module 13.2.2 - GraphToken).

Manages injection of Knowledge Graph Embeddings (KGE) into LLM context.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from khala.infrastructure.surrealdb.client import SurrealDBClient
from khala.domain.memory.value_objects import EmbeddingVector

logger = logging.getLogger(__name__)

class GraphTokenService:
    """Service to fetch and format KG tokens for LLM injection."""

    def __init__(self, db_client: SurrealDBClient):
        self.db_client = db_client

    async def get_kg_tokens(self, context_entities: List[str]) -> str:
        """
        Retrieve KGEs for given entities and format them as special tokens/text.
        """

        # 1. Fetch entity data + pre-computed embeddings
        embeddings = []
        for entity_id in context_entities:
            emb = await self._fetch_embedding(entity_id)
            if emb:
                embeddings.append(emb)

        if not embeddings:
            return ""

        # 2. Format as XML-like tokens (Simulated GraphToken)
        token_str = "<kg_context>\n"
        for item in embeddings:
            # We include the vector summary or raw data if applicable
            # item has 'summary' from entity.text and 'vector' from kg_embeddings
            # Ensure 'id' is present
            eid = item.get('id', 'unknown')
            summary = item.get('summary', 'Unknown Entity')
            token_str += f"  <entity id='{eid}'>{summary}</entity>\n"
        token_str += "</kg_context>"

        return token_str

    async def _fetch_embedding(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Fetch entity details and embeddings from DB."""

        # Try to fetch specialized KGE first
        query = """
        SELECT *, (SELECT text FROM entity WHERE id = $id) as entity_text
        FROM kg_embeddings
        WHERE entity_id = $id
        LIMIT 1;
        """
        async with self.db_client.get_connection() as conn:
            response = await conn.query(query, {"id": entity_id})

            # Check results
            if response and isinstance(response, list) and response:
                items = response
                if isinstance(response[0], dict) and 'result' in response[0]:
                    items = response[0]['result']

                if items and items[0]:
                    item = items[0]
                    # Structure return
                    return {
                        "id": entity_id,
                        "summary": item.get('entity_text', [None])[0] or "Unknown Entity",
                        "vector": item.get('embedding')
                    }

        # Fallback: Just fetch entity text if no specialized embedding found
        query_fallback = "SELECT id, text FROM entity WHERE id = $id;"
        async with self.db_client.get_connection() as conn:
            response = await conn.query(query_fallback, {"id": entity_id})
            if response and isinstance(response, list) and response:
                items = response
                if isinstance(response[0], dict) and 'result' in response[0]:
                    items = response[0]['result']
                if items:
                     return {
                        "id": entity_id,
                        "summary": items[0].get('text', "Unknown Entity"),
                        "vector": None
                    }
        return None
