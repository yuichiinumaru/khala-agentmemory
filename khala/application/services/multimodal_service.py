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
from khala.infrastructure.gemini.models import GEMINI_MULTIMODAL_EMBEDDING, GEMINI_PRO_2_5
from khala.domain.interfaces.blob_storage import BlobStorage

logger = logging.getLogger(__name__)

class MultimodalService:
    """Service for handling multimodal memory ingestion (Images)."""

    def __init__(
        self,
        memory_repository: MemoryRepository,
        gemini_client: GeminiClient,
        db_client: Optional[SurrealDBClient] = None,
        blob_storage: Optional[BlobStorage] = None
    ):
        self.repository = memory_repository
        self.gemini_client = gemini_client
        self.db_client = db_client or SurrealDBClient()
        self.blob_storage = blob_storage

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
            # 0. Upload to Blob Storage (if configured)
            storage_uri = None
            storage_provider = None
            
            if self.blob_storage:
                try:
                    # Determine naming convention
                    # Convention: {tier}/{user_id}/{date}/{filename}
                    # tier: 'chat' for user uploads, 'knowledge' for system/admin uploads
                    
                    is_system = user_id in ["system", "admin", "librarian"]
                    tier_folder = "knowledge" if is_system else "chat"
                    date_folder = datetime.now().strftime("%Y-%m-%d")
                    
                    # Original filename or generated one
                    base_filename = metadata.get("filename", f"img_{int(datetime.now().timestamp())}.{mime_type.split('/')[-1]}")
                    
                    # Clean filename logic could go here
                    
                    full_path = f"{tier_folder}/{user_id}/{date_folder}/{base_filename}"
                    
                    storage_uri = await self.blob_storage.upload(image_data, full_path, content_type=mime_type)
                    storage_provider = "minio" 
                    logger.info(f"Uploaded image to blob storage: {storage_uri}")
                except Exception as e:
                    logger.error(f"Failed to upload to blob storage: {e}")
                    # We continue even if upload fails, but omitting URI

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
                "analysis_model": analysis.get("model", GEMINI_PRO_2_5),
                "uri": storage_uri,
                "storage_provider": storage_provider,
                **(metadata or {})
            }

            memory = Memory(
                user_id=user_id,
                content=memory_content,
                tier=MemoryTier.SHORT_TERM, # Start in short term
                importance=ImportanceScore(0.8), # Images are usually important
                metadata=image_metadata,
                tags=["image", "multimodal"] + [e['name'] for e in entities if 'name' in e],
                embedding_visual=EmbeddingVector(values=visual_embedding, model=GEMINI_MULTIMODAL_EMBEDDING) if visual_embedding else None
            )

            # 3. Save Memory
            await self.repository.create(memory)
            logger.info(f"Ingested multimodal memory {memory.id} for user {user_id}")

            return memory.id

        except Exception as e:
            logger.error(f"Failed to ingest image: {e}")
            raise

    async def search_images_by_text(
        self,
        user_id: str,
        query_text: str,
        limit: int = 10,
        threshold: float = 0.6
    ) -> List[Dict[str, Any]]:
        """
        Cross-Modal Retrieval (Strategy 50).
        Find images that match a text query.

        Args:
            user_id: The user ID.
            query_text: The search query.
            limit: Maximum results.
            threshold: Similarity threshold.

        Returns:
            List of matching memories with similarity scores.
        """
        # 1. Generate text embedding using the same multimodal model
        # Note: We must use the multimodal-embedding model to be in the same space as visual embeddings
        try:
            import google.generativeai as genai

            # Using asyncio.to_thread for blocking SDK call
            result = await asyncio.to_thread(
                genai.embed_content,
                model=GEMINI_MULTIMODAL_EMBEDDING,
                content=query_text,
                task_type="retrieval_query",
                request_options={"timeout": 30}
            )

            query_embedding = result.get('embedding')
            if not query_embedding:
                logger.error("Failed to generate query embedding")
                return []

        except Exception as e:
            logger.error(f"Error embedding query: {e}")
            return []

        # 2. Vector Search against embedding_visual field
        # SurrealDB Query
        query = """
        SELECT *, vector::similarity::cosine(embedding_visual, $query_vec) as similarity
        FROM memory
        WHERE user_id = $uid
        AND embedding_visual IS NOT NONE
        AND vector::similarity::cosine(embedding_visual, $query_vec) > $threshold
        ORDER BY similarity DESC
        LIMIT $limit;
        """

        params = {
            "uid": user_id,
            "query_vec": query_embedding,
            "threshold": threshold,
            "limit": limit
        }

        try:
            async with self.db_client.get_connection() as conn:
                result = await conn.query(query, params)

                # Helper to parse result
                if isinstance(result, list) and len(result) > 0:
                    if isinstance(result[0], dict) and 'result' in result[0]:
                        return result[0]['result']
                    return result
                return []

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

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
                model=GEMINI_MULTIMODAL_EMBEDDING,
                content=blob,
                task_type="retrieval_document"
            )

            if 'embedding' in result:
                return result['embedding']
            return None
        except Exception as e:
            logger.warning(f"Failed to generate visual embedding: {e}")
            return None
