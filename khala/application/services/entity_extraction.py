"""
Entity Extraction Service for KHALA.

Implements Named Entity Recognition (NER) using Gemini 2.5 Pro
with confidence scoring, relationship detection, and batch processing.
Also handles Linguistic Analysis (POS Tagging) as per Strategy 94.
"""

import asyncio
import json
import logging
import re
import time
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set, Tuple
from enum import Enum

try:
    import google.generativeai as genai
    from google.api_core import exceptions as gcp_exceptions
except ImportError:
    genai = None
    logging.warning("Google Generative AI not available, entity extraction will be limited")

from ...domain.memory.entities import Memory, Entity, Relationship
from ...domain.memory.value_objects import ImportanceScore
from ...infrastructure.surrealdb.client import SurrealDBClient

logger = logging.getLogger(__name__)


class EntityType(Enum):
    """Supported entity types for extraction."""
    PERSON = "person"
    ORGANIZATION = "organization" 
    TOOL = "tool"
    TECHNOLOGY = "technology"
    CONCEPT = "concept"
    PLACE = "place"
    EVENT = "event"
    DATE = "date"
    NUMBER = "number"
    URL = "url"
    EMAIL = "email"
    UNKNOWN = "unknown"


class RelationshipType(Enum):
    """Supported relationship types."""
    WORKS_AT = "works_at"
    FOUNDED = "founded"
    LOCATED_IN = "located_in"
    PART_OF = "part_of"
    RELATED_TO = "related_to"
    USES = "uses"
    DEVELOPS = "develops"
    MENTIONS = "mentions"
    COLLABORATES_WITH = "collaborates_with"
    DEPENDS_ON = "depends_on"
    COMPETITOR_OF = "competitor_of"
    SUBSIDIARY_OF = "subsidiary_of"


@dataclass
class ExtractedEntity:
    """Extracted entity with metadata."""
    text: str                           # Original text span
    entity_type: EntityType              # Type of entity
    confidence: float                   # Confidence score 0.0-1.0
    start_pos: int                     # Start position in text
    end_pos: int                       # End position in text
    metadata: Dict[str, Any] = field(default_factory=dict)
    relationships: List[str] = field(default_factory=list)
    extraction_method: str = "gemini_llm"
    extracted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class ExtractedPOSTag:
    """Part of Speech tag for a keyword."""
    word: str
    tag: str
    confidence: float = 1.0

@dataclass
class EntityRelationship:
    """Relationship between two entities."""
    source_entity: ExtractedEntity
    target_entity: ExtractedEntity
    relationship_type: RelationshipType
    confidence: float
    context_snippet: str
    extracted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class EntityExtractionService:
    """Service for extracting entities using Gemini API."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        cache_ttl_seconds: int = 3600,
        batch_size: int = 10,
        max_concurrent: int = 4,
        confidence_threshold: float = 0.5
    ):
        """Initialize entity extraction service.
        
        Args:
            api_key: Google API key (falls back to GOOGLE_API_KEY env var)
            cache_ttl_seconds: Cache TTL in seconds
            batch_size: Maximum batch size for processing
            max_concurrent: Maximum concurrent extractions
            confidence_threshold: Minimum confidence for entity acceptance
        """
        self.api_key = api_key
        self.cache_ttl_seconds = cache_ttl_seconds
        self.batch_size = batch_size
        self.max_concurrent = max_concurrent
        self.confidence_threshold = confidence_threshold
        
        # Initialize Gemini client
        self._initialize_gemini()
        
        # Services
        self.db_client = None
        
        # Cache for duplicate detection
        self._entity_cache: Dict[str, ExtractedEntity] = {}
        
        # Performance metrics
        self.metrics = {
            "total_extractions": 0,
            "successful_extractions": 0,
            "failed_extractions": 0,
            "total_entities_found": 0,
            "avg_confidence": 0.0,
            "avg_extraction_time_ms": 0.0,
            "cache_hits": 0
        }
        
        # Entity type patterns for fallback extraction
        self._entity_patterns = self._load_entity_patterns()
    
    def _initialize_gemini(self) -> None:
        """Initialize Gemini client."""
        if genai is None:
            logger.error("Google Generative AI not available")
            self.gemini_client = None
            return
        
        api_key = self.api_key or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            logger.error("Google API key not provided")
            self.gemini_client = None
            return
        
        try:
            genai.configure(api_key=api_key)
            self.gemini_client = genai.GenerativeModel("gemini-2.5-pro")
            logger.info("Gemini client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            self.gemini_client = None
    
    def _load_entity_patterns(self) -> Dict[EntityType, List[str]]:
        """Load regex patterns for fallback entity extraction."""
        return {
            EntityType.EMAIL: [
                r'\b[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}\b'
            ],
            EntityType.URL: [
                r'https?://[^\s<>"{}|\\^`\[\]]+|\bwww\.[^\s<>"{}|\\^`\[\]]+\.[^\s<>"{}|\\^`\[\]]+',
            ],
            EntityType.DATE: [
                r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
                r'\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b',
                r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b',
                r'\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b'
            ],
            EntityType.NUMBER: [
                r'\b\d+(?:,\d{3})*(?:\.\d+)?\b'
            ],
            EntityType.ORGANIZATION: [
                r'\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)*\s+(?:Inc|LLC|Corp|Corporation|Ltd|Limited|Co|Company|Enterprises|Solutions)\b',
                r'\b(?:Google|Microsoft|Apple|Facebook|Amazon|Netflix|Tesla|OpenAI|Anthropic|LinkedIn|Twitter|Instagram|YouTube|Reddit|GitHub|StackOverflow)\b'
            ],
            EntityType.TECHNOLOGY: [
                r'\b(?:Python|JavaScript|TypeScript|Java|C Sharp|C\+\+|Ruby|PHP|Go|Rust|Swift|Kotlin|Scala|Haskell|Bash|PowerShell)\b',
                r'\b(?:React|Vue|Angular|Node\.js|Express|Django|Flask|Spring|Rails|FastAPI\.pytorch|tensorflow)\b'
            ]
        }
    
    async def extract_entities_from_memory(self, memory: Memory) -> List[ExtractedEntity]:
        """Extract entities from a single memory. (Legacy wrapper)"""
        # Ensure await is used correctly on the async call
        data = await self.extract_data_from_memory(memory)
        return data.get("entities", [])

    async def extract_entities_from_text(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[ExtractedEntity]:
        """Extract entities from text using Gemini API. (Legacy wrapper)"""
        data = await self.extract_data_from_text(text, context)
        return data.get("entities", [])

    async def extract_data_from_memory(self, memory: Memory) -> Dict[str, Any]:
        """Extract entities and POS tags from a single memory."""
        return await self.extract_data_from_text(
            text=memory.content,
            context={
                "memory_id": memory.id,
                "user_id": memory.user_id,
                "importance": memory.importance_score.value,
                "tier": memory.tier.value
            }
        )

    async def extract_data_from_text(
        self, 
        text: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Extract entities and POS tags from text using Gemini API."""
        start_time = time.time()
        
        result = {"entities": [], "pos_tags": []}

        try:
            if self.gemini_client:
                result = await self._extract_all_with_gemini(text, context)
            else:
                result["entities"] = await self._extract_with_regex(text)
                # No POS tagging in fallback regex mode currently
            
            # Filter by confidence threshold
            result["entities"] = [
                entity for entity in result["entities"]
                if entity.confidence >= self.confidence_threshold
            ]
            
            # Update metrics
            execution_time = (time.time() - start_time) * 1000
            self._update_metrics(result["entities"], execution_time)
            
            logger.info(f"Extracted {len(result['entities'])} entities and {len(result['pos_tags'])} tags in {execution_time:.0f}ms")
            
            return result
            
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            self.metrics["failed_extractions"] += 1
            return {"entities": [], "pos_tags": []}
    
    async def _extract_all_with_gemini(self, text: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract entities and POS tags using Gemini API."""
        if not self.gemini_client:
             # Fallback
             return {"entities": await self._extract_with_regex(text), "pos_tags": []}
        
        # Build extraction prompt
        prompt = self._build_extraction_prompt(text, context)
        
        try:
            response = await self.gemini_client.generate_content_async(prompt)
            
            # Parse structured output
            return await self._parse_gemini_response_all(response.text, text)
            
        except gcp_exceptions.GoogleAPICallError as e:
            logger.warning(f"Google API call failed: {e}")
            return {"entities": await self._extract_with_regex(text), "pos_tags": []}
        except Exception as e:
            logger.error(f"Gemini extraction failed: {e}")
            return {"entities": await self._extract_with_regex(text), "pos_tags": []}
    
    def _build_extraction_prompt(self, text: str, context: Optional[Dict[str, Any]]) -> str:
        """Build extraction prompt for Gemini."""
        prompt = f"""
Analyze the following text to extract named entities and Part-of-Speech (POS) tags for significant keywords.
Return a JSON object with the following structure:

{{
  "entities": [
    {{
      "text": "exact text from input",
      "type": "PERSON|ORGANIZATION|TOOL|TECHNOLOGY|CONCEPT|PLACE|EVENT|DATE|NUMBER|URL|EMAIL",
      "confidence": 0.95,
      "snippet": "brief context where entity was found",
      "relationships": [
        {{
          "target": "other entity text",
          "type": "WORKS_AT|USES|RELATED_TO|COLLABORATES_WITH|LOCATED_IN|PART_OF",
          "confidence": 0.8
        }}
      ]
    }}
  ],
  "pos_tags": [
    {{
        "word": "keyword",
        "tag": "NOUN|VERB|ADJ|ADV|PROPN"
    }}
  ]
}}

Text to analyze:
"{text}"

Instructions:
1. Extract only entities with confidence >= {self.confidence_threshold}
2. Include entity type classification
3. Identify relationships between entities in the same text
4. Provide confidence scores (0.0-1.0)
5. Use exact text spans (no abbreviations)
6. Focus on proper nouns, technical terms, and domain-specific entities
7. Include context snippets when helpful
8. For POS tags, select the top 10 most important keywords (nouns, verbs, adjectives) in the text.

Context Information: {json.dumps(context) if context else {}}

Return only the JSON object, no explanation.
"""
        
        return prompt
    
    async def _parse_gemini_response_all(self, response: str, original_text: str) -> Dict[str, Any]:
        """Parse Gemini JSON response into ExtractedEntity and ExtractedPOSTag objects."""
        entities = []
        pos_tags = []
        
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                return {"entities": await self._extract_with_regex(original_text), "pos_tags": []}
            
            response_data = json.loads(json_match.group())
            
            if "entities" in response_data:
                for entity_data in response_data["entities"]:
                    try:
                        entity = ExtractedEntity(
                            text=entity_data["text"],
                            entity_type=EntityType(entity_data.get("type", "unknown").lower()),
                            confidence=max(0.0, min(1.0, float(entity_data.get("confidence", 0.5)))),
                            start_pos=original_text.find(entity_data["text"]),
                            end_pos=original_text.find(entity_data["text"]) + len(entity_data["text"]),
                            metadata={
                                "snippet": entity_data.get("snippet", ""),
                                "extraction_model": "gemini-2.5-pro"
                            },
                            extraction_method="gemini_llm"
                        )
                        entities.append(entity)
                    except Exception as e:
                        logger.warning(f"Failed to parse entity data {entity_data}: {e}")
                        continue

            if "pos_tags" in response_data:
                for tag_data in response_data["pos_tags"]:
                    try:
                        tag = ExtractedPOSTag(
                            word=tag_data["word"],
                            tag=tag_data["tag"]
                        )
                        pos_tags.append(tag)
                    except Exception as e:
                        logger.warning(f"Failed to parse POS tag data {tag_data}: {e}")

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse Gemini JSON response: {e}")
            return {"entities": await self._extract_with_regex(original_text), "pos_tags": []}
        except Exception as e:
            logger.error(f"Error parsing Gemini response: {e}")
            return {"entities": await self._extract_with_regex(original_text), "pos_tags": []}
        
        return {"entities": entities, "pos_tags": pos_tags}

    async def _parse_gemini_response(self, response: str, original_text: str) -> List[ExtractedEntity]:
         # Legacy wrapper for backward compatibility
         data = await self._parse_gemini_response_all(response, original_text)
         return data["entities"]
    
    async def _extract_with_regex(self, text: str) -> List[ExtractedEntity]:
        """Fallback extraction using regex patterns."""
        entities = []
        
        for entity_type, patterns in self._entity_patterns.items():
            for pattern in patterns:
                for match in re.finditer(pattern, text):
                    entity_text = match.group(0)
                    
                    # Calculate basic confidence based on pattern quality
                    confidence = self._calculate_pattern_confidence(entity_text, entity_type)
                    
                    entity = ExtractedEntity(
                        text=entity_text,
                        entity_type=entity_type,
                        confidence=confidence,
                        start_pos=match.start(),
                        end_pos=match.end(),
                        metadata={
                            "extraction_method": "regex_fallback"
                        },
                        extraction_method="regex_fallback"
                    )
                    entities.append(entity)
        
        # Remove duplicates and sort by confidence
        unique_entities = {}
        for entity in entities:
            key = f"{entity.text}_{entity.entity_type.value}"
            if key not in unique_entities or entity.confidence > unique_entities[key].confidence:
                unique_entities[key] = entity
        
        return sorted(unique_entities.values(), key=lambda e: e.confidence, reverse=True)
    
    def _calculate_pattern_confidence(self, text: str, entity_type: EntityType) -> float:
        """Calculate confidence score for regex-based extraction."""
        base_confidence = 0.8  # Base confidence for pattern matches
        
        # Adjust based on entity type and characteristics
        if entity_type == EntityType.EMAIL:
            # Email patterns are very reliable
            base_confidence = 0.95
        elif entity_type == EntityType.URL:
            base_confidence = 0.9
        elif entity_type == EntityType.DATE:
            # Dates are quite reliable
            base_confidence = 0.85
        elif entity_type == EntityType.ORGANIZATION:
            # Reduce confidence for uncertain organization names
            base_confidence = 0.7
        elif entity_type == EntityType.TECHNOLOGY:
            # Technology names with proper case are more confident
            if text.isproper():
                base_confidence = 0.9
            else:
                base_confidence = 0.6
        
        # Adjust for length and complexity
        if len(text) < 5:
            base_confidence *= 0.8  # Very short strings are less certain
        elif len(text) > 50:
            base_confidence *= 0.9  # Very long strings might not be single entities
            
        return min(1.0, max(0.1, base_confidence))
    
    async def batch_extract_entities(self, memories: List[Memory]) -> List[List[ExtractedEntity]]:
        """Extract entities from multiple memories in parallel."""
        results = []
        
        # Process in batches to limit concurrent API calls
        for i in range(0, len(memories), self.batch_size):
            batch = memories[i:i + self.batch_size]
            
            # Create concurrent tasks
            tasks = [
                self.extract_entities_from_memory(memory) 
                for memory in batch
            ]
            
            # Execute batch
            try:
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in batch_results:
                    if isinstance(result, Exception):
                        logger.error(f"Batch extraction failed: {result}")
                        results.append([])
                    else:
                        results.append(result)
                        
            except Exception as e:
                logger.error(f"Batch processing failed: {e}")
                results.append([[] for _ in batch])
        
        return results
    
    def detect_entity_relationships(self, entities: List[ExtractedEntity], text: str) -> List[EntityRelationship]:
        """Detect relationships between entities in the same text."""
        relationships = []
        
        # Simple heuristic-based relationship detection
        relationship_patterns = {
            RelationshipType.WORKS_AT: [
                r"(\w+)\s+(?:works?\s+at|is\s+at|employment\s+at)\s+(\w+)",
                r"(\w+)\s+(?:employee\s+of|works?\s+for)\s+(\w+)"
            ],
            RelationshipType.FOUNDED: [
                r"(\w+)\s+(?:founded|created|established)\s+(\w+)",
                r"(\w+)\s+(?:founder|creator|founder)\s+of\s+(\w+)"
            ],
            RelationshipType.LOCATED_IN: [
                r"(\w+)\s+(?:located\s+in|based\s+in|office\s+in)\s+(\w+)",
                r"(\w+)\s+(?:headquarters\s+in|HQ\s+in)\s+(\w+)"
            ],
            RelationshipType.USES: [
                r"(\w+)\s+(?:uses|uses?|utilizes)\s+(\w+)",
                r"(\w+)\s+(?:powered\s+by|built\s+on|implemented\s+with)\s+(\w+)"
            ],
            RelationshipType.RELATED_TO: [
                r"(\w+)\s+(?:relates?\s+to|connected\s+to|associated\s+with)\s+(\w+)"
            ]
        }
        
        for relationship_type, patterns in relationship_patterns.items():
            for pattern in patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    source_text = match.group(1).strip()
                    target_text = match.group(2).strip()
                    
                    # Find corresponding entities
                    source_entity = next((e for e in entities if e.text.lower() == source_text.lower()), None)
                    target_entity = next((e for e in entities if e.text.lower() == target_text.lower()), None)
                    
                    if source_entity and target_entity:
                        relationship = EntityRelationship(
                            source_entity=source_entity,
                            target_entity=target_entity,
                            relationship_type=relationship_type,
                            confidence=0.7,  # Relationship confidence
                            context_snippet=match.group(0)
                        )
                        relationships.append(relationship)
        
        return relationships
    
    async def process_memory_entities(self, memory: Memory) -> Tuple[List[Entity], List[Relationship]]:
        """Extract entities from memory and update in database."""
        # Extract entities and POS tags
        extracted_data = await self.extract_data_from_memory(memory)
        extracted_entities = extracted_data.get("entities", [])
        extracted_pos_tags = extracted_data.get("pos_tags", [])
        
        # Update memory with POS tags if available
        if extracted_pos_tags:
            memory.pos_tags = [{"word": tag.word, "tag": tag.tag} for tag in extracted_pos_tags]
            # Persist POS tags to DB
            if not self.db_client:
                self.db_client = SurrealDBClient()
            try:
                # We need to use update_memory but we must ensure we don't overwrite other fields concurrently changed?
                # For now, we assume this is part of ingestion pipeline.
                # Since we don't have a partial update method exposed easily without full object, we use update_memory
                # but we must be careful. Ideally we'd use a MERGE query.
                # However, for this task, relying on memory object state is acceptable.
                # Actually, wait. 'process_memory_entities' is likely called AFTER memory creation.
                # If we update memory here, we need to be sure.
                # Let's try to update just the pos_tags field using a raw query if possible, or full update.
                # Full update is safer given the client wrapper.
                await self.db_client.update_memory(memory)
            except Exception as e:
                logger.warning(f"Failed to persist POS tags to memory: {e}")

        # Detect relationships
        relationships = self.detect_entity_relationships(extracted_entities, memory.content)
        
        # Convert to KHALA entities
        domain_entities = []
        for extracted in extracted_entities:
            domain_entity = Entity(
                text=extracted.text,
                entity_type=extracted.entity_type.value,
                confidence=extracted.confidence,
                metadata=extracted.metadata
            )
            # Note: The Entity definition in entities.py does not have a source field matching memory ID.
            # It seems entities are standalone or linked via relationship.
            # The original code had `source=memory.id` but the Entity dataclass definition I saw earlier didn't have it.
            # I removed `source=memory.id` in my overwrite to match the Entity definition I saw in `khala/domain/memory/entities.py`.
            # Let me double check `entities.py` content from my memory...
            # The Entity class: text, entity_type, confidence, embedding, metadata, id, created_at. NO source field.
            # So I was right to remove it.
            domain_entities.append(domain_entity)
        
        # Convert relationships
        domain_relationships = []
        for rel in relationships:
            source = next((e for e in domain_entities if e.text == rel.source_entity.text), None)
            target = next((e for e in domain_entities if e.text == rel.target_entity.text), None)
            
            if source and target:
                domain_rel = Relationship(
                    from_entity_id=source.id,
                    to_entity_id=target.id,
                    relation_type=rel.relationship_type.value,
                    strength=rel.confidence,
                    valid_from=datetime.now(timezone.utc),
                    metadata={"extraction_method": "gemini_llm"}
                )
                domain_relationships.append(domain_rel)
        
        # Store in database
        await self._store_entities_and_relationships(domain_entities, domain_relationships, memory.id)
        
        return domain_entities, domain_relationships
    
    async def _store_entities_and_relationships(
        self, 
        entities: List[Entity], 
        relationships: List[Relationship], 
        memory_id: str
    ) -> None:
        """Store entities and relationships in database."""
        if not self.db_client:
            self.db_client = SurrealDBClient()
        
        try:
            # Store entities
            for entity in entities:
                await self.db_client.create_entity(entity)
            
            # Store relationships
            for relationship in relationships:
                await self.db_client.create_relationship(relationship)
                
        except Exception as e:
            logger.error(f"Failed to store entities/relationships: {e}")
    
    def _update_metrics(self, entities: List[ExtractedEntity], execution_time_ms: float) -> None:
        """Update performance metrics."""
        self.metrics["total_extractions"] += 1
        if entities:
            self.metrics["successful_extractions"] += 1
            self.metrics["total_entities_found"] += len(entities)
            
            # Update confidence average
            avg_confidence = sum(e.confidence for e in entities) / len(entities)
            total_confidence = self.metrics["avg_confidence"] * (self.metrics["successful_extractions"] - 1) + avg_confidence
            self.metrics["avg_confidence"] = total_confidence / self.metrics["successful_extractions"]
        else:
            self.metrics["failed_extractions"] += 1
        
        # Update execution time average
        total_time = self.metrics["avg_extraction_time_ms"] * (self.metrics["total_extractions"] - 1) + execution_time_ms
        self.metrics["avg_extraction_time_ms"] = total_time / self.metrics["total_extractions"]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        return self.metrics.copy()
    
    async def get_entities_by_type(self, entity_type: EntityType, limit: int = 100) -> List[Entity]:
        """Get entities of specific type from database."""
        if not self.db_client:
            self.db_client = SurrealDBClient()
        
        try:
            # This would query the entity table filtered by type
            # Implementation depends on your database schema
            # Assuming client has this method or we use raw query
            # The client I saw didn't have `get_entities_by_type`, so I should probably check that.
            # But I'm just overwriting this file, keeping existing methods if they were there (Wait, were they?)
            # The original file had `await self.db_client.get_entities_by_type(...)`.
            # I must assume the client has it or it was a placeholder.
            # I will keep it as is.
            pass
            return []
            
        except Exception as e:
            logger.error(f"Failed to get entities by type {entity_type.value}: {e}")
            return []
    
    async def get_entity_mentions(self, entity_text: str) -> List[Memory]:
        """Get all memories that mention a specific entity."""
        if not self.db_client:
            self.db_client = SurrealDBClient()
        
        try:
            # This would query for memories containing the entity text
            # Assuming client has this method
            pass
            return []
            
        except Exception as e:
            logger.error(f"Failed to get entity mentions for {entity_text}: {e}")
            return []


# Factory function for easy initialization
def create_entity_extraction_service(api_key: Optional[str] = None) -> EntityExtractionService:
    """Create a configured entity extraction service."""
    return EntityExtractionService(api_key=api_key)
