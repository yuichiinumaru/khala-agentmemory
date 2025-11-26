"""Domain services for the skill library.

These services contain business logic for managing and retrieving skills.
"""

import logging
from typing import List, Optional, Dict, Any

from .entities import Skill
from .repositories import SkillRepository
from .value_objects import SkillType, SkillLanguage
from ..memory.value_objects import EmbeddingVector

logger = logging.getLogger(__name__)

class SkillLibraryService:
    """Service for managing the skill library."""
    
    def __init__(self, repository: SkillRepository):
        self.repository = repository
        
    async def register_skill(self, skill: Skill) -> str:
        """Register a new skill in the library."""
        # Check if skill with same name exists
        existing = await self.repository.get_by_name(skill.name)
        if existing:
            raise ValueError(f"Skill with name '{skill.name}' already exists")
            
        skill_id = await self.repository.create(skill)
        logger.info(f"Registered new skill: {skill.name} ({skill_id})")
        return skill_id
        
    async def update_skill(self, skill: Skill) -> None:
        """Update an existing skill."""
        # Verify existence
        existing = await self.repository.get_by_id(skill.id)
        if not existing:
            raise ValueError(f"Skill with ID {skill.id} not found")
            
        await self.repository.update(skill)
        logger.info(f"Updated skill: {skill.name} ({skill.id})")
        
    async def get_skill(self, name_or_id: str) -> Optional[Skill]:
        """Retrieve a skill by name or ID."""
        # Try as ID first (UUID format check could be added)
        skill = await self.repository.get_by_id(name_or_id)
        if skill:
            return skill
            
        # Try as name
        return await self.repository.get_by_name(name_or_id)
        
    async def register_skill_from_code(self, code: str, language: str = "python") -> str:
        """Register a new skill by parsing its code.
        
        Args:
            code: The source code of the skill.
            language: The programming language (default: "python").
            
        Returns:
            str: The ID of the registered skill.
            
        Raises:
            ValueError: If code analysis fails or no function is found.
        """
        from ..code_analysis.services import CodeAnalysisService
        from ..code_analysis.value_objects import CodeElementType
        from .value_objects import SkillParameter
        
        # Analyze code
        analysis_service = CodeAnalysisService()
        result = analysis_service.analyze_code(code, language)
        
        if result.errors:
            raise ValueError(f"Code analysis failed: {'; '.join(result.errors)}")
            
        if not result.functions:
            raise ValueError("No function definition found in code")
            
        # Use the first function as the skill
        func_def = result.functions[0]
        
        # Map args to SkillParameters
        parameters = [
            SkillParameter(
                name=arg,
                type="Any", # Parser doesn't extract arg types yet
                description="Parameter extracted from code"
            ) for arg in func_def.args
        ]
        
        # Create Skill entity
        skill = Skill(
            name=func_def.name,
            description=func_def.docstring or "No description provided",
            code=code,
            language=SkillLanguage(language.lower()),
            skill_type=SkillType.ATOMIC,
            parameters=parameters,
            return_type=func_def.return_type,
            # We could add imports as dependencies if we wanted
        )
        
        return await self.register_skill(skill)

    async def search_skills(
        self, 
        query: str, 
        embedding: Optional[EmbeddingVector] = None,
        limit: int = 5
    ) -> List[Skill]:
        """Search for skills using hybrid search (Vector + Text)."""
        results = []
        seen_ids = set()
        
        # 1. Vector Search (if embedding provided)
        if embedding:
            vector_results = await self.repository.search_by_vector(
                embedding, top_k=limit
            )
            for skill in vector_results:
                if skill.id not in seen_ids:
                    results.append(skill)
                    seen_ids.add(skill.id)
        
        # 2. Text Search (BM25)
        # Only fetch more if we haven't reached the limit
        if len(results) < limit:
            text_results = await self.repository.search_by_text(
                query, top_k=limit
            )
            for skill in text_results:
                if skill.id not in seen_ids:
                    results.append(skill)
                    seen_ids.add(skill.id)
                    
        return results[:limit]
