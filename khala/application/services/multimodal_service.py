from typing import Dict, Any, Optional, List, Union
import logging
import asyncio
from datetime import datetime, timezone
import base64

from khala.domain.memory.entities import Memory, MemoryTier, ImportanceScore
from khala.domain.memory.value_objects import EmbeddingVector
from khala.domain.memory.repository import MemoryRepository
from khala.infrastructure.gemini.client import GeminiClient
from khala.infrastructure.surrealdb.client import SurrealDBClient

logger = logging.getLogger(__name__)

class MultimodalService:
    """Service for handling multimodal memory ingestion (Images)."""

    def __init__(
        self,
        memory_repository: MemoryRepository,
        gemini_client: GeminiClient,
        db_client: Optional[SurrealDBClient] = None
    ):
        self.repository = memory_repository
        self.gemini_client = gemini_client
        self.db_client = db_client or SurrealDBClient()

    async def ingest_image(
        self,
        user_id: str,
        image_data: bytes,
        mime_type: str,
        context: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Ingest an image as a memory.

        Analyzes the image using Gemini, creates a text description,
        generates a visual embedding, and stores it as a memory.

        Args:
            user_id: The user ID.
            image_data: Raw bytes of the image.
            mime_type: MIME type (e.g., 'image/jpeg').
            context: Optional context about the image.
            metadata: Additional metadata.

        Returns:
            The ID of the created memory.
        """
        try:
            # 1. Analyze and Embed in parallel
            analysis_task = self._analyze_image(image_data, mime_type, context)
            embedding_task = self._generate_visual_embedding(image_data, mime_type)

            analysis, visual_embedding = await asyncio.gather(analysis_task, embedding_task)

            description = analysis.get("description", "")
            entities = analysis.get("entities", [])

            # 2. Create Memory
            # We store the detailed description as the memory content
            memory_content = f"[Image Analysis] {description}"
            if context:
                memory_content += f"\nContext: {context}"

            # Metadata for the image
            image_metadata = {
                "type": "image",
                "mime_type": mime_type,
                "size_bytes": len(image_data),
                "entities_detected": entities,
                "analysis_model": analysis.get("model", "gemini-2.5-pro"),
                **(metadata or {})
            }

            memory = Memory(
                user_id=user_id,
                content=memory_content,
                tier=MemoryTier.SHORT_TERM, # Start in short term
                importance=ImportanceScore(0.8), # Images are usually important
                metadata=image_metadata,
                tags=["image", "multimodal"] + [e['name'] for e in entities if 'name' in e],
                embedding_visual=EmbeddingVector(values=visual_embedding, model="multimodal-embedding-001") if visual_embedding else None
            )

            # 3. Save Memory
            await self.repository.create(memory)
            logger.info(f"Ingested multimodal memory {memory.id} for user {user_id}")

            return memory.id

        except Exception as e:
            logger.error(f"Failed to ingest image: {e}")
            raise

    async def _analyze_image(
        self,
        image_data: bytes,
        mime_type: str,
        context: Optional[str]
    ) -> Dict[str, Any]:
        """Analyze image using Gemini Vision capabilities."""

        # Prepare the image object for Gemini
        image_blob = {
            'mime_type': mime_type,
            'data': image_data
        }

        prompt = """
        Analyze this image in detail.
        1. Provide a comprehensive description of the visual content.
        2. Identify key entities (people, objects, text, locations).
        3. Describe the mood or atmosphere if applicable.

        Output format:
        Description: <detailed description>
        Entities: <comma separated list>
        """

        if context:
            prompt += f"\nAdditional Context: {context}"

        response = await self.gemini_client.generate_text(
            prompt=prompt,
            images=[image_blob],
            task_type="generation"
        )

        content = response.get("content", "")

        # Parse the response (simple parsing)
        description = content
        entities = []

        # Try to extract sections if formatted
        if "Description:" in content:
            parts = content.split("Entities:")
            description = parts[0].replace("Description:", "").strip()
            if len(parts) > 1:
                entity_str = parts[1].strip()
                entities = [{"name": e.strip()} for e in entity_str.split(",")]

        return {
            "description": description,
            "entities": entities,
            "model": response.get("model_id"),
            "raw_response": content
        }

    async def _generate_visual_embedding(self, image_data: bytes, mime_type: str) -> Optional[List[float]]:
        """Generate visual embedding for an image."""
        try:
            import google.generativeai as genai

            blob = {'mime_type': mime_type, 'data': image_data}

            # Note: Assuming genai.embed_content supports this per Google documentation
            # for 'models/multimodal-embedding-001' or similar
            result = await asyncio.to_thread(
                genai.embed_content,
                model="models/multimodal-embedding-001",
                content=blob,
                task_type="retrieval_document"
            )

            if 'embedding' in result:
                return result['embedding']
            return None
        except Exception as e:
            logger.warning(f"Failed to generate visual embedding: {e}")
            return None
