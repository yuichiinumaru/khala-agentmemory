"""Integration tests for Skill Library."""

import pytest
from typing import List, Optional
from khala.domain.skills.services import SkillLibraryService
from khala.domain.skills.repositories import SkillRepository
from khala.domain.skills.entities import Skill
from khala.domain.memory.value_objects import EmbeddingVector

class InMemorySkillRepository(SkillRepository):
    """In-memory repository for testing."""
    
    def __init__(self):
        self.store = {}
        
    async def create(self, skill: Skill) -> str:
        self.store[skill.id] = skill
        return skill.id
        
    async def get_by_id(self, skill_id: str) -> Optional[Skill]:
        return self.store.get(skill_id)
        
    async def get_by_name(self, name: str) -> Optional[Skill]:
        for skill in self.store.values():
            if skill.name == name:
                return skill
        return None
        
    async def update(self, skill: Skill) -> None:
        self.store[skill.id] = skill
        
    async def delete(self, skill_id: str) -> None:
        if skill_id in self.store:
            del self.store[skill_id]
            
    async def search_by_vector(self, embedding: EmbeddingVector, top_k: int = 5, min_similarity: float = 0.6) -> List[Skill]:
        return []
        
    async def search_by_text(self, query_text: str, top_k: int = 5) -> List[Skill]:
        return []

@pytest.mark.asyncio
async def test_register_skill_from_code():
    repo = InMemorySkillRepository()
    service = SkillLibraryService(repo)
    
    code = """
def calculate_sum(a: int, b: int) -> int:
    '''Calculates the sum of two numbers.'''
    return a + b
"""
    
    skill_id = await service.register_skill_from_code(code)
    
    skill = await service.get_skill(skill_id)
    assert skill is not None
    assert skill.name == "calculate_sum"
    assert skill.description == "Calculates the sum of two numbers."
    assert skill.return_type == "int"
    assert len(skill.parameters) == 2
    assert skill.parameters[0].name == "a"
    assert skill.parameters[1].name == "b"

@pytest.mark.asyncio
async def test_register_skill_from_code_no_function():
    repo = InMemorySkillRepository()
    service = SkillLibraryService(repo)
    
    code = "x = 1"
    
    with pytest.raises(ValueError, match="No function definition found"):
        await service.register_skill_from_code(code)
