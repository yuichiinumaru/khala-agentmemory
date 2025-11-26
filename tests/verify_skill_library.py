import asyncio
import logging
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from khala.domain.skills.entities import Skill
from khala.domain.skills.value_objects import SkillType, SkillLanguage, SkillParameter
from khala.domain.memory.value_objects import EmbeddingVector
from khala.infrastructure.surrealdb.client import SurrealDBClient
from khala.infrastructure.persistence.skill_repository import SurrealSkillRepository
from khala.domain.skills.services import SkillLibraryService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    logger.info("Starting Skill Library Verification...")
    
    # Initialize client
    client = SurrealDBClient(
        url="ws://localhost:8000/rpc",
        namespace="khala_test",
        database="skills_test"
    )
    
    try:
        await client.initialize()
        
        # Initialize repository and service
        repo = SurrealSkillRepository(client)
        service = SkillLibraryService(repo)
        
        # 1. Create a Skill
        logger.info("1. Creating a Skill...")
        skill = Skill(
            name="calculate_fibonacci",
            description="Calculates the nth Fibonacci number efficiently.",
            code="def fib(n): return n if n <= 1 else fib(n-1) + fib(n-2)",
            language=SkillLanguage.PYTHON,
            skill_type=SkillType.ATOMIC,
            parameters=[
                SkillParameter(name="n", type="int", description="The position in Fibonacci sequence")
            ],
            return_type="int",
            tags=["math", "algorithm"],
            embedding=EmbeddingVector([0.1] * 768) # Mock embedding
        )
        
        skill_id = await service.register_skill(skill)
        logger.info(f"Skill created with ID: {skill_id}")
        
        # 2. Retrieve Skill
        logger.info("2. Retrieving Skill...")
        retrieved_skill = await service.get_skill(skill_id)
        if retrieved_skill:
            logger.info(f"Retrieved skill: {retrieved_skill.name}")
            assert retrieved_skill.name == "calculate_fibonacci"
            assert retrieved_skill.language == SkillLanguage.PYTHON
        else:
            logger.error("Failed to retrieve skill")
            
        # 3. Search Skill (Vector)
        logger.info("3. Searching Skill (Vector)...")
        search_embedding = EmbeddingVector([0.1] * 768)
        results = await service.search_skills("fibonacci", embedding=search_embedding)
        logger.info(f"Found {len(results)} skills via vector search")
        assert len(results) > 0
        assert results[0].name == "calculate_fibonacci"
        
        # 4. Search Skill (Text)
        logger.info("4. Searching Skill (Text)...")
        results = await service.search_skills("Calculates the nth Fibonacci")
        logger.info(f"Found {len(results)} skills via text search")
        # Note: Text search might depend on SurrealDB indexing which might take a moment or config
        
        # 5. Update Skill
        logger.info("5. Updating Skill...")
        retrieved_skill.update_code("def fib_optimized(n): ...")
        await service.update_skill(retrieved_skill)
        
        updated_skill = await service.get_skill(skill_id)
        logger.info(f"Updated code: {updated_skill.code}")
        assert updated_skill.code == "def fib_optimized(n): ..."
        
        logger.info("Verification Complete!")
        
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
