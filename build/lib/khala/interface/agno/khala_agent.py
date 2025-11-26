"""
KHALA-enhanced Agent with advanced memory capabilities.

Integrates KHALA memory system, search, verification, and multi-agent
coordination with Agno framework for intelligent AI agents.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field

# Try to import Agno, but provide fallback if not available
try:
    from agno import Agent, Message, Model
    AGNO_AVAILABLE = True
except ImportError:
    AGNO_AVAILABLE = False
    logging.warning("Agno framework not available, using fallback implementation")

from ...domain.memory.entities import Memory, MemoryTier
from ...domain.memory.value_objects import ImportanceScore
from ...application.verification.verification_gate import VerificationGate
from ...application.services.entity_extraction import EntityExtractionService
from ...infrastructure.cache.cache_manager import CacheManager
from ...infrastructure.surrealdb.client import SurrealDBClient

logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Configuration for KHALA agent."""
    model: Dict[str, Any] = field(default_factory=lambda: {
        "provider": "google",
        "model_id": "gemini-2.5-pro", 
        "temperature": 0.7,
        "max_tokens": 4096
    })
    memory: MemoryConfig = field(default_factory=lambda: {
        "cache_levels": ["l1", "l2", "l3"],
        "auto_verification": True,
        "entity_extraction": True,
        "relationship_detection": True,
        "conversation_memory": True
    })
    verification: VerificationConfig = field(default_factory=lambda: {
        "consensus_required": True,
        "verification_interval": "conversation",
        "confidence_threshold": 0.8,
        "parallel_agents": 4
    })
    cache: Dict[str, Any] = field(default_factory=lambda: {
        "l1_max_mb": 100,
        "l1_ttl_seconds": 300,
        "l2_ttl_seconds": 3600,
        "l3_ttl_seconds": 86400
    })


@dataclass
class MemoryConfig:
    """Configuration for memory system."""
    cache_levels: List[str] = field(default_factory=lambda: ["l1", "l2", "l3"])
    auto_verification: bool = True
    entity_extraction: bool = True
    relationship_detection: bool = True
    conversation_memory: bool = True


@dataclass
class VerificationConfig:
    """Configuration for verification system."""
    consensus_required: bool = True
    verification_interval: str = "conversation"
    confidence_threshold: float = 0.8
    parallel_agents: int = 4
    auto_retry: bool = True
    max_retries: int = 3


@dataclass
class ConversationContext:
    """Context for conversation processing."""
    conversation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    session_metadata: Dict[str, Any] = field(default_factory=dict)
    current_context: List[Dict[str, Any]] = field(default_factory=list)
    accessed_memories: List[str] = field(default_factory=list)
    extracted_entities: List[str] = field(default_factory=list)


class KHALAAgent:
    """Intelligent agent with advanced KHALA memory capabilities."""
    
    def __init__(
        self,
        name: str,
        description: str,
        config: Optional[AgentConfig] = None,
        model_kwargs: Optional[Dict[str, Any]] = None
    ):
        """Initialize KHALA agent."""
        self.name = name
        self.description = description
        self.config = config or AgentConfig()
        
        # Core systems
        self.cache_manager = None
        self.memory_provider = None
        self.verification_gate = None
        self.entity_extractor = None
        self.db_client = None
        
        # Conversation state
        self.current_conversation = None
        self.conversation_history: List[ConversationContext] = []
        self.active_memories: Dict[str, Memory] = {}
        
        # Initialize systems
        self._init_systems()
        
        # Initialize Agno agent if available
        if AGNO_AVAILABLE:
            try:
                self._init_agno_agent(model_kwargs or {})
            except Exception as e:
                logger.error(f"Failed to initialize Agno agent: {e}")
                self._init_fallback_agent()
        else:
            self._init_fallback_agent()
    
    def _init_systems(self) -> None:
        """Initialize KHALA subsystems."""
        try:
            # Initialize cache manager
            self.cache_manager = CacheManager(
                l1_max_mb=self.config.cache["l1_max_mb"],
                l1_ttl_seconds=self.config.cache["l1_ttl_seconds"],
                l2_ttl_seconds=self.config.cache["l2_ttl_seconds"],
                l3_ttl_seconds=self.config.cache["l3_ttl_seconds"]
            )
            asyncio.create_task(self.cache_manager.start())
            
            # Initialize memory provider
            self.memory_provider = KHALAMemoryProvider(
                cache_manager=self.cache_manager
            )
            
            # Initialize verification gate
            self.verification_gate = VerificationGate(
                gemini_api_key=os.getenv("GOOGLE_API_KEY"),
                enable_cascading=True,
                cache_ttl_seconds=300
            )
            
            # Initialize entity extraction
            self.entity_extractor = EntityExtractionService(
                api_key=os.getenv("GOOGLE_API_KEY"),
                max_concurrent=self.config.verification.parallel_agents
            )
            
            # Initialize database client
            self.db_client = SurrealDBClient()
            
        except Exception as e:
            logger.error(f"Failed to initialize KHALA systems: {e}")
            raise
    
    def _init_agno_agent(self, model_kwargs: Dict[str, Any]) -> None:
        """Initialize Agno framework agent."""
        try:
            # Create model configuration
            model_config = {
                **self.config.model,
                **model_kwargs
            }
            
            # Create Agno model
            self.agno_model = Model(
                id=self.config.model["model_id"],
                temperature=self.config.model["temperature"],
                max_tokens=self.config.model["max_tokens"]
            )
            
            # Create Agno agent
            self.agno_agent = Agent(
                model=self.agno_model,
                name=self.name,
                description=self.description,
                instructions=[
                    "You are an intelligent AI assistant with advanced memory capabilities.",
                    "Access stored knowledge through the KHALA memory system when needed.",
                    "Remember and recall information from previous conversations.",
                    "Extract and understand entities mentioned in conversations.",
                    "Provide responses that build on your knowledge and understanding."
                ],
                tools=[
                    # Memory tools
                    self._create_memory_tools(),
                    # Search tools
                    self._create_search_tools(),
                    self._create_verification_tools()
                ]
            )
            
            logger.info(f"Agno agent initialized for {self.name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Agno agent: {e}")
            raise
    
    def _init_fallback_agent(self) -> None:
        """Initialize fallback agent implementation."""
        logger.info(f"Using fallback agent implementation for {self.name}")
        self.agno_agent = None
        # Fallback implementation would go here
        # For now, we'll handle requests manually
    
    async def start(self) -> None:
        """Start the agent and all subsystems."""
        try:
            # Ensure systems are started
            if not self.cache_manager.started:
                await self.cache_manager.start()
                
            logger.info(f"KHALA agent {self.name} started")
            
        except Exception as e:
            logger.error(f"Failed to start KHALA agent {self.name}: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop the agent and cleanup resources."""
        try:
            if self.cache_manager.started:
                await self.cache_manager.stop()
            
            logger.info(f"KHALA agent {self.name} stopped")
            
        except Exception as e:
            logger.error(f"Failed to stop KHALA agent {self.name}: {e}")
    
    async def process_message(self, message: str, user_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process user message and generate response."""
        if context is None:
            context = {}
        
        if self.agno_agent:
            return await self._process_with_agno(message, user_id, context)
        else:
            return await self._process_fallback(message, user_id, context)
    
    async def _process_with_agno(self, message: str, user_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process message using Agno framework."""
        try:
            # Get or create conversation context
            convo_context = self._get_conversation_or_create(user_id, context)
            
            # Extract entities from message
            if self.config.memory.entity_extraction:
                entities = await self.entity_extractor.extract_entities_from_text(message, {
                    "conversation_id": convo_context.conversation_id,
                    "user_id": user_id
                })
                
                # Store entities and update context
                for entity in entities:
                    convo_context.extracted_entities.append(entity.text)
                
                # Build memory from entities for search context
                entity_memories = await self._build_memory_from_entities(entities)
                
                # Update conversation context with entities
                convo_context.extracted_entities.extend([e.text for e in entities])
            
            # Search for relevant memories
            memory_context = ""
            if convo_context.extracted_entities:
                # Build context string from entity meanings
                entity_context = ", ".join(convo_context.extracted_entities)
                memory_context = f"Relevant context: {entity_context}"
            
            # Perform hybrid search in memory
            relevant_memories = []
            if self.cache_manager and memory_context:
                try:
                    cache_key = self.cache_manager.generate_cache_key(
                        "memory_search",
                        message,
                        context=memory_context
                    )
                    cached_search = await self.cache_manager.get(cache_key, CacheLevel.L2)
                    if cached_search:
                        relevant_memories = cached_search
                    else:
                        # Perform search using KHALA search service
                        from ...search.services import HybridSearchService
                        
                        search_service = HybridSearchService()
                        query_str = f"{message} {memory_context}".strip()
                        
                        # Create search intent
                        from ...search.value_objects import Query, SearchIntent
                        
                        query = Query(
                            text=query_str,
                            intent=SearchIntent.classify_text(query_str),
                            embedding=None,
                            user_id=user_id,
                            filters={},
                            limit=10
                        )
                        
                        search_results = await search_service.search(query)
                        relevant_memories = [result.result for result in search_results]
                        
                        # Cache search results
                        await self.cache_manager.put(cache_key, search_results, ttl_seconds=1800)
                except Exception as e:
                    logger.error(f"Memory search failed: {e}")
            
            # Enhance conversation context with relevant memories
            if relevant_memories:
                for memory_data in relevant_memories[:5]:  # Limit context size
                    convo_context.current_context.append({
                        "memory_id": memory_data.id,
                        "relevance": memory_data.get("relevance", 0.5),
                        "content": memory_data.get("content", "")[:200],  # Preview
                        "access_count": memory_data.get("access_count", 0)
                    })
            
            # Update conversation memory
            if self.config.memory.conversation_memory:
                conversation_memory = Memory(
                    user_id=user_id,
                    content=f"User: {message}",
                    tier=MemoryTier.WORKING,
                    importance=ImportanceScore.medium(),
                    metadata={
                        "conversation_id": convo_context.conversation_id,
                        "message_type": "user_message",
                        "context_entities": convo_context.extracted_entities,
                        "relevant_memories": [m.id for m in relevant_memories]
                    }
                )
                
                # Process conversation memory
                processed_memory, relationships = await self.memory_provider.process_memory_entities(conversation_memory)
                
                # Update active memories
                self.active_memories[processed_memory.id] = processed_memory
                
                # Add to conversation history
                convo_context.accessed_memories.append(processed_memory.id)
                if relationships:
                    convo_context.extracted_entities.extend([r.target_entity for rel in relationships])
            
            # Generate response
            if self.agno_agent:
                try:
                    # Create enhanced context for Agno
                    agno_context = {
                        "conversation_context": convo_context,
                        "relevant_memories": relevant_memories,
                        "domain_knowledge": self.get_domain_knowledge()
                    }
                    
                    # Process through Agno
                    response = await self.agno_agent.process_message(
                        message=message,
                        context=agno_context,
                        user_id=user_id
                    )
                    
                    # Store response as memory if high confidence
                    if response.get("confidence", 0) > 0.8:
                        response_memory = Memory(
                            user_id=user_id, 
                            content=response.get("content", message),
                            tier=MemoryTier.SHORT_TERM,
                            importance=ImportanceScore.high(),
                            metadata={
                                "conversation_id": convo_context.conversation_id,
                                "message_type": "agent_response",
                                "confidence": response.get("confidence", 0.5),
                                "model_used": response.get("model", "gemini-2.5-pro")
                            }
                        )
                        
                        await self.memory_provider.process_memory_entities(response_memory)
                        self.active_memories[response_memory.id] = response_memory
                    
                    return response
                    
                except Exception as e:
                    logger.error(f"Agno processing failed: {e}")
                    # Fallback processing
                    return await self._process_fallback(message, user_id, context)
            
            return {
                "response": message,
                "agent": self.name,
                "confidence": 0.5,
                "context": convo_context,
                "method": "fallback"
            }
            
        else:
            return await self._process_fallback(message, user_id, context)
    
    def _create_memory_tools(self) -> List[Any]:
        """Create memory management tools."""
        try:
            memory_search_tool = MemorySearchTool(self.memory_provider, self.cache_manager)
            memory_verify_tool = MemoryVerificationTool(self.verification_gate)
            return [memory_search_tool, memory_verify_tool]
        except Exception as e:
            logger.error(f"Failed to create memory tools: {e}")
            return []
    
    def _create_search_tools(self) -> List[Any]:
        """Create search tools."""
        try:
            return [MemorySearchTool(self.memory_provider, self.cache_manager)]
        except Exception as e:
            logger.error(f"Failed to create search tools: {e}")
            return []
    
    def _create_verification_tools(self) -> List[Any]:
        """Create verification tools."""
        try:
            return [MemoryVerificationTool(self.verification_gate)]
        except Exception as e:
            logger.error(f"Failed to create verification tools: {e}")
            return []
    
    async def _process_fallback(self, message: str, user_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback message processing when Agno is unavailable."""
        try:
            # Basic response with memory awareness
            response_text = f"I understand: {message}"
            
            if self.cache_manager:
                cache_key = self.cache_manager.generate_cache_key("fallback_response", message, user_id=user_id)
                cached_response = await self.cache_manager.get(cache_key)
                if cached_response:
                    response_text = cached_response
                else:
                    await self.cache_manager.put(cache_key, response_text, ttl_seconds=300)
            
            return {
                "response": response_text,
                "agent": self.name,
                "confidence": 0.3,
                "method": "fallback"
            }
            
        except Exception as e:
            logger.error(f"Fallback processing failed: {e}")
            return {
                "response": f"I processed: {message}",
                "agent": self.name,
                "confidence": 0.1,
                "method": "basic_fallback"
            }
    
    def _get_conversation_or_create(self, user_id: str, context: Dict[str, Any]) -> ConversationContext:
        """Get existing conversation or create new one."""
        # For simplicity, create new context each time
        # In production, this would manage conversation sessions
        return ConversationContext(
            user_id=user_id,
            session_metadata={
                **context,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        )
    
    def _build_memory_from_entities(self, entities: List) -> List[Dict[str, Any]]:
        """Build memory objects from extracted entities."""
        return [
            {
                "id": hash(entity.text + entity.type.value) % 10000000,
                "text": entity.text,
                "entity_type": entity.entity_type.value,
                "confidence": entity.confidence,
                "metadata": {
                    "extraction_method": entity.extraction_method,
                    "start_pos": entity.start_pos,
                    "end_pos": entity.end_pos,
                    "created_at": entity.extracted_at.isoformat()
                },
                "tags": [entity.entity_type.value]
            }
            for entity in entities
        ]
    
    def get_domain_knowledge(self) -> str:
        """Get domain knowledge base."""
        # This would be expanded with domain-specific knowledge
        base_knowledge = """
        Domain Knowledge:
        - KHALA memory system with 57 optimization strategies
        - Three-tier memory hierarchy (working/short_term/long_term)
        - Hybrid search with vector + BM25 + metadata
        - Multi-agent verification with consensus
        - LLM cascading for cost optimization
        
        Current Capabilities:
        - Parallel memory processing with multiple agents
        - Entity extraction and relationship detection
        - Automatic memory consolidation and verification
        - Intelligent caching with multiple levels
        - Real-time search and retrieval
        """
        return base_knowledge
    
    async def get_memory_context(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed context for a specific memory."""
        if memory_id in self.active_memories:
            memory = self.active_memories[memory_id]
            return {
                "id": memory.id,
                "content": memory.content,
                "tier": memory.tier.value,
                "importance": memory.importance_score.value,
                "created_at": memory.created_at.isoformat(),
                "access_count": memory.access_count,
                "verification_score": memory.verification_score,
                "related_entities": [entity.id for entity in memory.related_entities],
                "relationships": [
                    {
                        "source": rel.source,
                        "target": rel.target,
                        "type": rel.relation_type.value,
                        "strength": rel.strength
                    }
                    for rel in memory.relationships
                ]
            }
        return None
    
    async def store_new_memory(self, content: str, user_id: str, **kwargs) -> str:
        """Store new memory with automatic processing."""
        memory = Memory(
            user_id=user_id,
            content=content,
            tier=kwargs.get("tier", MemoryTier.WORKING),
            importance=ImportanceScore(kwargs.get("importance", 0.7)),
            metadata=kwargs.get("metadata", {})
        )
        
        # Process memory through KHALA systems
        processed_memory, relationships = await self.memory_provider.process_memory_entities(memory)
        
        # Store in active memories
        self.active_memories[processed_memory.id] = processed_memory
        
        return processed_memory.id
    
    async def update_memory(self, memory_id: str, updates: Dict[str, Any]) -> bool:
        """Update existing memory."""
        if memory_id not in self.active_memories:
            return False
        
        try:
            memory = self.active_memories[memory_id]
            
            # Update fields
            if "content" in updates:
                memory.content = updates["content"]
            if "tier" in updates:
                memory.tier = MemoryTier(updates["tier"])
            if "importance" in updates:
                memory.importance_score = ImportanceScore(updates["importance"])
            
            metadata_updates = {k: v for k, v in updates.items() if hasattr(memory, k) and not callable(getattr(memory, k))}
            memory.metadata.update(metadata_updates)
            
            # Update database
            db_updates = {k: v for k, v in memory.to_dict().items() if k != 'id'}
            if db_updates:
                db_updates["updated_at"] = datetime.now(timezone.utc).isoformat()
                await self.db_client.update_memory(memory_id, db_updates)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update memory {memory_id}: {e}")
            return False
    
    async def get_conversation_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get conversation history for a user."""
        """Implementation would return conversation history from database."""
        # Simplified implementation - would query database in production
        return [
            {
                "conversation_id": ctx.conversation_id,
                "user_id": ctx.user_id,
                "messages": ctx.current_context,
                "memory_count": len(ctx.accessed_memories),
                "entity_count": len(ctx.extracted_entities),
                "created_at": ctx.session_metadata.get("created_at")
            }
            for ctx in self.conversation_history[-5:] if hasattr(ctx, "session_metadata")
        ]
    
    def get_agent_metrics(self) -> Dict[str, Any]:
        """Get comprehensive agent performance metrics."""
        metrics = {
            "agent_name": self.name,
            "memory_provider": "active" if self.memory_provider else "inactive",
            "verification_gate": "active" if self.verification_gate else "inactive",
            "entity_extractor": "active" if self.entity_extractor else "inactive",
            "cache_manager": "active" if self.cache_manager else "inactive",
            "database_client": "connected" if self.db_client else "disconnected",
            "agno_integration": "active" if self.agno_agent else "fallback"
        }
        
        # Add cache metrics
        if self.cache_manager:
            cache_metrics = self.cache_manager.get_metrics()
            metrics["cache"] = cache_metrics
        
        # Add conversation statistics
        metrics["conversations"] = len(self.conversation_history)
        metrics["active_memories"] = len(self.active_memories)
        metrics["total_memory_accesses"] = sum(m.access_count for m in self.active_memories.values())
        
        return metrics


def create_khala_agent(
    name: str,
    description: str,
    config: Optional[AgentConfig] = None,
    **kwargs
) -> KHALAAgent:
    """Create configured KHALA agent."""
    return KHALAAgent(name, description, config, **kwargs)


# Domain-specific agent templates
def create_research_agent() -> KHALAAgent:
    """Create research-focused KHALA agent."""
    config = AgentConfig(
        model={
            "model_id": "gemini-2.5-pro",
            "temperature": 0.1,
            "max_tokens": 4096
        },
        memory=MemoryConfig(
            cache_levels=["l1", "l2", "l3"],
            auto_verification=True,
            entity_extraction=True,
            relationship_detection=True
        ),
        verification=VerificationConfig(
            consensus_required=True,
            confidence_threshold=0.9,
            parallel_agents=6
        )
    )
    
    return KHALAAgent(
        name="Research Agent",
        description="AI research assistant with advanced memory capabilities",
        config=config,
        **kwargs
    )


def create_technical_agent(domain: str) -> KHALAAgent:
    """Create domain-technical specialist agent."""
    config = AgentConfig(
        model={
            "model_id": "gemini-2.5-pro",
            "temperature": 0.1,
            "max_tokens": 4096
        },
        memory=MemoryConfig(
            cache_levels=["l1", "l2"],
            auto_verification=False,
            entity_extraction=True,
            relationship_detection=False
        ),
        verification=VerificationConfig(
            consensus_required=False,
            confidence_threshold=0.7,
            parallel_agents=2
        )
    )
    
    return KHALAAgent(
        name=f"{domain} Agent",
        description=f"Technical specialist for {domain} development and analysis",
        config=config,
        domain=domain
    )


# Example usage
if __name__ == "__main__":
    async def test_khala_agent():
        """Test KHALA agent functionality."""
        # Create agent
        agent = create_research_agent()
        
        # Start agent
        await agent.start()
        
        # Test conversation
        response = await agent.process_message(
            "What do you know about machine learning models?",
            user_id="test_user"
        )
        
        print(f"Response: {response['response']}")
        print(f"Confidence: {response['confidence']}")
        print(f"Method: {response['method']}")
        
        # Test memory storage
        memory_id = await agent.store_new_memory(
            content="Agent testing memory storage capability",
            user_id="test_user",
            importance=0.8
        )
        
        print(f"Stored memory with ID: {memory_id}")
        
        # Test memory retrieval
        context = await agent.get_memory_context(memory_id)
        if context:
            print(f"Memory context: {context['content'][:100]}...")
        
        # Stop agent
        await agent.stop()

if __name__ == "__main__":
    asyncio.run(test_khala_agent())
