"""SurrealDB implementation of the SkillRepository."""

import logging
from typing import List, Optional

from khala.domain.skills.repositories import SkillRepository
from khala.domain.skills.entities import Skill
from khala.domain.memory.value_objects import EmbeddingVector
from khala.infrastructure.surrealdb.client import SurrealDBClient

logger = logging.getLogger(__name__)

class SurrealSkillRepository(SkillRepository):
    """SurrealDB implementation of the SkillRepository interface."""
    
    def __init__(self, client: SurrealDBClient):
        self.client = client
        
    async def create(self, skill: Skill) -> str:
        """Save a new skill."""
        return await self.client.create_skill(skill)
        
    async def get_by_id(self, skill_id: str) -> Optional[Skill]:
        """Retrieve a skill by its ID."""
        return await self.client.get_skill(skill_id)
        
    async def get_by_name(self, name: str) -> Optional[Skill]:
        """Retrieve a skill by its name."""
        # This requires a specific query not in the base client
        # We can implement it using a custom query here
        query = "SELECT * FROM skill WHERE name = $name LIMIT 1;"
        params = {"name": name}
        
        async with self.client.get_connection() as conn:
            response = await conn.query(query, params)
            
            if not response:
                return None
                
            if isinstance(response, list) and len(response) > 0:
                item = response[0]
                if isinstance(item, dict):
                    if 'status' in item and 'result' in item:
                        if item['status'] == 'OK' and item['result']:
                            return self.client._deserialize_skill(item['result'][0])
                    else:
                        return self.client._deserialize_skill(item)
            
            return None
        
    async def update(self, skill: Skill) -> None:
        """Update an existing skill."""
        await self.client.update_skill(skill)
        
    async def delete(self, skill_id: str) -> None:
        """Delete a skill."""
        await self.client.delete_skill(skill_id)
        
    async def search_by_vector(
        self, 
        embedding: EmbeddingVector, 
        top_k: int = 5, 
        min_similarity: float = 0.6
    ) -> List[Skill]:
        """Search skills by vector similarity."""
        results = await self.client.search_skills_by_vector(
            embedding=embedding,
            top_k=top_k,
            min_similarity=min_similarity
        )
        return [self.client._deserialize_skill(data) for data in results]
        
    async def search_by_text(
        self, 
        query_text: str, 
        top_k: int = 5
    ) -> List[Skill]:
        """Search skills by text (BM25/Full-text)."""
        results = await self.client.search_skills_by_text(
            query_text=query_text,
            top_k=top_k
        )
        return [self.client._deserialize_skill(data) for data in results]
