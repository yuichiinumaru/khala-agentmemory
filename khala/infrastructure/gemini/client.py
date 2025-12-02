"""Gemini API client with LLM cascading optimization.

This module provides intelligent model routing, cost optimization,
and connection management for the Google Gemini API.
"""

import asyncio
import json
import time
import hashlib
from decimal import Decimal
from typing import Dict, List, Optional, Any, Union, Tuple, Type, TypeVar
from datetime import datetime, timezone, timedelta
import logging

try:
    from pydantic import BaseModel
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    # Define a dummy BaseModel for type hinting if pydantic is missing
    class BaseModel: pass

try:
    import google.generativeai as genai
    from google.api_core import exceptions as gcp_exceptions
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
except ImportError as e:
    raise ImportError(
        "Google Generative AI is required. Install with: pip install google-generativeai"
    ) from e

from .models import GeminiModel, ModelTier, ModelRegistry
from .cost_tracker import CostTracker

logger = logging.getLogger(__name__)


class GeminiClient:
    """Gemini API client with intelligent cascading and cost optimization."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        cost_tracker: Optional[CostTracker] = None,
        enable_cascading: bool = True,
        enable_caching: bool = True,
        cache_ttl_seconds: int = 300,  # 5 minutes
        max_retries: int = 3,
        timeout_seconds: int = 30,
        concurrency_limit: int = 10
    ):
        """Initialize Gemini client.
        
        Args:
            api_key: Google API key (if None, uses GOOGLE_API_KEY env var)
            cost_tracker: CostTracker instance for usage tracking
            enable_cascading: Enable intelligent model cascading
            enable_caching: Enable response caching
            cache_ttl_seconds: Cache TTL in seconds
            max_retries: Maximum retry attempts
            timeout_seconds: Request timeout in seconds
            concurrency_limit: Maximum concurrent requests to the API
        """
        self.api_key = api_key or self._get_api_key_from_env()
        self.cost_tracker = cost_tracker or CostTracker()
        self.enable_cascading = enable_cascading
        self.enable_caching = enable_caching
        self.cache_ttl_seconds = cache_ttl_seconds
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        
        # Concurrency control
        self._semaphore = asyncio.Semaphore(concurrency_limit)

        # Response cache
        self._response_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        
        # Model configuration
        self._models: Dict[str, genai.GenerativeModel] = {}
        
        # Metrics
        self._prompt_classification_cache: Dict[str, str] = {}  # Cache prompt classifications
        self._complexity_cache: Dict[str, float] = {}  # Cache complexity scores

        self.T = TypeVar("T", bound=BaseModel)
        self.cache_hits = 0
        self.cache_misses = 0
    
        # Initialize models if cascading is enabled
        if self.enable_cascading:
            self._setup_models()
    
    def get_api_key(self) -> str:
        """Get the API key for authentication."""
        return self.api_key
    
    def _get_api_key_from_env(self) -> str:
        """Get API key from environment variable."""
        import os
        
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError(
                "GOOGLE_API_KEY environment variable is not set. "
                "Please set GOOGLE_API_KEY or provide api_key parameter."
            )
        return api_key
    
    def _setup_models(self) -> None:
        """Initialize all configured models."""
        try:
            genai.configure(api_key=self.api_key)
            
            for model_id, model_config in ModelRegistry.MODELS.items():
                if model_config.supports_embeddings:
                    # Initialize embedding model
                    self._models[model_id] = genai.GenerativeModel(
                        model_name=model_config.model_id
                    )
                else:
                    # Initialize generation model
                    self._models[model_id] = genai.GenerativeModel(
                        model_name=model_config.model_id,
                        generation_config=genai.types.GenerationConfig(
                            temperature=model_config.temperature,
                            max_output_tokens=model_config.max_tokens,
                            top_p=model_config.top_p,
                            top_k=model_config.top_k
                        ),
                        safety_settings={
                            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
                            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
                            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
                            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
                        }
                    )
                    
            logger.info(f"Initialized {len(self._models)} Gemini models")
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini models: {e}")
            raise
    
    async def classify_task_complexity(self, prompt: str) -> float:
        """Classify task complexity score using simple heuristics.
        
        Args:
            prompt: The prompt to classify
            
        Returns:
            Complexity score (0.0-1.0)
        """
        # Check cache first
        cache_key = hash(prompt)
        if cache_key in self._complexity_cache:
            return self._complexity_cache[cache_key]
        
        complexity = 0.0
        prompt_lower = prompt.lower()
        
        # Factor analysis for complexity
        factors = {
            # Length-based complexity
            "length": min(1.0, len(prompt) / 1000),  # 1000 chars = 1.0 complexity
            # Question complexity
            "questions": min(1.0, prompt.count("?") / 5), # 5 questions = 1.0 complexity
            # Code/technical content
            "code": min(1.0, prompt.count("```") * 0.2),  # Each code block = 0.2 complexity
            # Structured data
            "json": min(1.0, prompt.count(":") / 20),  # 20 colons = 1.0 complexity
            # Multi-part tasks
            "steps": min(1.0, prompt_lower.count("step") / 10),  # 10 steps = 1.0 complexity
            # Analysis tasks
            "analysis": min(1.0, prompt_lower.count("analyze") / 5),

        }
        
        # Weighted combination
        weights = {
            "length": 0.2,
            "questions": 0.2, 
            "code": 0.3,
            "json": 0.2,
            "steps": 0.2,
            "analysis": 0.2
        }
        
        complexity = sum(factors[factor] * weights[factor] for factor in factors)
        
        # Cache result
        self._complexity_cache[cache_key] = complexity
        
        return min(1.0, complexity)
    
    def classify_task_type(self, prompt: str) -> str:
        """Classify the type of task based on prompt content.
        
        Args:
            prompt: The prompt to classify
            
        Returns:
            Task type string (embedding, generation, classification, etc.)
        """
        prompt_lower = prompt.lower()
        
        # Check for embedding request
        if any(keyword in prompt_lower for keyword in ["embed", "vector", "similarity"]):
            return "embedding"
        
        # Check for classification/tasks
        if any(keyword in prompt_lower for keyword in ["classify", "category", "intent", "categorize"]):
            return "classification"
        
        # Check for entity extraction
        if any(keyword in prompt_lower for keyword in ["extract", "entity", "mentioned", "person"]):
            return "extraction"
        
        # Default to generation
        return "generation"
    
    def select_model(self, prompt: str, task_type: str = "generation") -> GeminiModel:
        """Select the optimal model based on task complexity and type.
        
        Args:
            prompt: The prompt to classify
            task_type: Type of task
            
        Returns:
            Selected model configuration
        """
        if not self.enable_cascading:
            # If cascading is disabled, use smart tier
            return ModelRegistry.get_model("gemini-2.5-pro")
        
        # Classify complexity
        complexity = asyncio.create_task(self.classify_task_complexity(prompt))
        
        # Determine required quality based on task type
        quality_requirements = {
            "embedding": 0.5,  # Embeddings don't need highest quality
            "classification": 0.7,  # Moderate quality needed
            "extraction": 0.8,   # High quality needed for extraction
            "generation": 0.8    # High quality needed for generation
        }.get(task_type, 0.8)
        
        # Get cost-optimal model
        try:
            complexity_value = complexity if isinstance(complexity, float) else 0.5
            
            if hasattr(complexity, "__await__"):
                try:
                    loop = asyncio.get_running_loop()
                    # If we are in a loop, we can't use asyncio.run. 
                    # We have to assume a default or handle it differently.
                    # For synchronous select_model, we might need to rely on the cache or default.
                    if loop.is_running():
                         # We can't await here because select_model is sync.
                         # Fallback to default complexity
                         complexity_score = 0.5
                    else:
                        complexity_score = asyncio.run(complexity)
                except RuntimeError:
                    # No running loop, safe to use asyncio.run
                    complexity_score = asyncio.run(complexity)
            else:
                complexity_score = complexity_value
                
            return ModelRegistry.get_cost_optimal_model(complexity_score, quality_requirements)
        except Exception as e:
            logger.warning(f"Error selecting optimal model, using default: {e}")
            return ModelRegistry.get_model("gemini-2.5-pro")
    
    async def generate_text(
        self,
        prompt: str,
        images: Optional[List[Any]] = None,
        model_id: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        task_type: str = "generation",
        use_cascading: bool = True
    ) -> Dict[str, Any]:
        """Generate text using the optimal or specified model.
        
        Args:
            prompt: Text prompt for generation
            images: Optional list of images (PIL.Image or blob)
            model_id: Specific model to use (overrides cascading)
            temperature: Override model temperature
            max_tokens: Override max tokens
            task_type: Type of task for classification
            use_cascading: Whether to use model cascading
            
        Returns:
            Response dictionary with content, metadata, and cost info
        """
        start_time = time.time()
        
        # Select model
        # If images are provided, force use of a multimodal model (gemini-2.5-pro or flash)
        if images:
            if not model_id:
                # Default to Flash for multimodal as it's efficient, or Pro if quality needed
                # For now, let's use the one selected by complexity, but ensure it supports images.
                # All Gemini models in our registry (Pro/Flash) support images.
                model = self.select_model(prompt, task_type)
            else:
                model = ModelRegistry.get_model(model_id)
                use_cascading = False
        elif model_id:
            model = ModelRegistry.get_model(model_id)
            use_cascading = False
        else:
            model = self.select_model(prompt, task_type)
        
        # Check cache if enabled (skip for images for now as hashing them is expensive)
        if self.enable_caching and not images:
            cache_key = self._get_cache_key(prompt, model_id=model.model_id)
            cached_response = self._get_cached_response(cache_key)
            if cached_response:
                logger.debug(f"Cache hit for {model.model_id}")
                self.cache_hits += 1
                return cached_response
            # Record miss
            self.cache_misses += 1
        
        # Configure generation parameters
        config = {
            "temperature": temperature or model.temperature,
            "max_output_tokens": max_tokens or model.max_tokens,
        }
        
        # Initialize model if needed
        if model.model_id not in self._models:
            try:
                if model.supports_embeddings:
                    self._models[model.model_id] = genai.GenerativeModel(
                        model_name=model.model_id
                    )
                else:
                    self._models[model.model_id] = genai.GenerativeModel(
                        model_name=model.model_id,
                        generation_config=genai.types.GenerationConfig(
                            temperature=config["temperature"],
                            max_output_tokens=config["max_output_tokens"],
                            top_p=model.top_p,
                            top_k=model.top_k
                        )
                    )
            except Exception as e:
                logger.error(f"Failed to initialize model {model.model_id}: {e}")
                raise
        
        # Prepare content
        content_parts = [prompt]
        if images:
            content_parts.extend(images)

        # Execute generation with retries
        model_instance = self._models[model.model_id]
        
        for attempt in range(self.max_retries + 1):
            try:
                async with self._semaphore:
                    response = await model_instance.generate_content_async(
                        content_parts,
                        stream=False,
                        request_options={"timeout": self.timeout_seconds}
                    )
                break
            except gcp_exceptions.GoogleAPIError as e:
                if attempt == self.max_retries:
                    logger.error(f"Failed after {self.max_retries} attempts: {e}")
                    raise
                logger.warning(f"Attempt {attempt + 1} failed, retrying: {e}")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        # Calculate tokens (approximate)
        input_tokens = len(prompt.split()) * 1.3  # Rough estimate
        output_tokens = len(response.text.split()) * 1.3
        response_time_ms = (time.time() - start_time) * 1000
        
        # Record cost
        cost_record = self.cost_tracker.record_call(
            model=model,
            input_tokens=int(input_tokens),
            output_tokens=int(output_tokens),
            response_time_ms=response_time_ms,
            task_type=task_type,
            success=True
        )
        
        # Cache response if enabled
        if self.enable_caching:
            cache_key = self._get_cache_key(prompt, model_id=model.model_id)
            cached_data = {
                "content": response.text,
                "model_id": model.model_id,
                "model_tier": model.tier.value,
                "cache_hit": False,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "response_time_ms": response_time_ms,
                "input_tokens": int(input_tokens),
                "output_tokens": int(output_tokens),
                "cost_usd": str(cost_record.cost_usd)
            }
            self._cache_response(cache_key, cached_data)
        
        return {
            "content": response.text,
            "model_id": model.model_id,
            "model_tier": model.tier.value,
            "cache_hit": False,
            "response_time_ms": response_time_ms,
            "input_tokens": int(input_tokens),
            "output_tokens": int(output_tokens),
            "cost_usd": float(cost_record.cost_usd),
            "model_name": model.name
        }
    
    async def generate_embeddings(
        self,
        texts: List[str],
        model_id: Optional[str] = None
    ) -> List[List[float]]:
        """Generate embeddings for list of texts.
        
        Args:
            texts: List of texts to embed
            model_id: Specific model to use
            
        Returns:
            List of embedding vectors
        """
        embedding_model = ModelRegistry.get_embedding_model()
        
        # Initialize embedding model if needed
        # Note: EmbeddingModel is separate from GenerativeModel
        if embedding_model.model_id not in self._models:
             # For embeddings we use genai.embed_content directly usually, but if we want to cache the model object:
             pass
        
        embeddings = []
        batch_size = 100  # Process in batches
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            try:
                async with self._semaphore:
                    # genai.embed_content is sync. Run in executor.
                    loop = asyncio.get_running_loop()
                    result = await loop.run_in_executor(
                        None,
                        lambda: genai.embed_content(
                            model=embedding_model.model_id,
                            content=batch,
                            task_type="retrieval_document",
                            output_dimensionality=embedding_model.embedding_dimensions,
                            request_options={"timeout": self.timeout_seconds}
                        )
                    )
                # result['embedding'] is a list of embeddings
                embeddings.extend(result['embedding'])
            except Exception as e:
                logger.error(f"Failed to embed batch {i//batch_size}: {e}")
                raise
        
        # Record costs
        for text, embedding in zip(texts, embeddings):
            # Calculate tokens (rough estimate)
            tokens = len(text.split()) * 1.3
            self.cost_tracker.record_call(
                model=embedding_model,
                input_tokens=int(tokens),
                output_tokens=0,  # Embeddings don't have output tokens
                response_time_ms=100.0,  # Rough estimate
                task_type="embedding",
                success=True
            )
        
        return embeddings
    
    def _get_cache_key(self, content: str, prefix: str = "", model_id: str = "") -> str:
        """Generate cache key.

        Args:
            content: Content to cache
            prefix: Cache key prefix
            model_id: Model identifier

        Returns:
            Cache key
        """
        # Create base hash from content
        content_hash = hashlib.md5(content.encode()).hexdigest()[:16]

        # Build cache key
        components = []
        if prefix:
            components.append(prefix)
        if model_id:
            components.append(model_id)
        components.append(content_hash)

        return "_".join(components)
    
    def _get_cached_response(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached response if available and not expired.
        
        Args:
            cache_key: Cache key to retrieve

        Returns:
            Cached response or None
        """
        if not self.enable_caching:
            return None
        
        cached_record = self._response_cache.get(cache_key)
        if not cached_record:
            return None
        
        # Check if cache has expired
        now = datetime.now(timezone.utc)

        # Handle different ways timestamp might be stored (in record or in separate dict)
        if "timestamp" in cached_record:
            if isinstance(cached_record["timestamp"], str):
                 cache_time = datetime.fromisoformat(cached_record["timestamp"])
            else:
                 cache_time = cached_record["timestamp"]
        else:
            cache_time = self._cache_timestamps.get(cache_key, now)

        age_seconds = (now - cache_time).total_seconds()

        if age_seconds > self.cache_ttl_seconds:
            # Remove expired cache entry
            if cache_key in self._response_cache:
                del self._response_cache[cache_key]
            if cache_key in self._cache_timestamps:
                del self._cache_timestamps[cache_key]
            return None
        
        # Update cache hit tracking
        if cache_key not in self._cache_timestamps:
            self._cache_timestamps[cache_key] = now

        cached_record["cache_hit"] = True
        return cached_record

    def _cache_response(self, cache_key: str, data: Dict[str, Any]) -> None:
        """Cache a response with timestamp."""
        self._response_cache[cache_key] = data
        self._cache_timestamps[cache_key] = datetime.now(timezone.utc)
    
    def get_cost_tracker(self) -> CostTracker:
        """Get the cost tracker instance."""
        return self.cost_tracker
    
    def clear_cache(self) -> None:
        """Clear all cached responses."""
        self._response_cache.clear()
        self._cache_timestamps.clear()
        logger.info("Cleared response cache")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total) if total > 0 else 0.0

        return {
            "hits": self.cache_hits,
            "misses": self.cache_misses,
            "total": total,
            "hit_rate": hit_rate,
            "size": len(self._response_cache)
        }

    def get_budget_status(self) -> Dict[str, Any]:
        """Get current budget status and alerts."""
        return self.cost_tracker.get_budget_status()
    
    def get_optimization_report(self) -> Dict[str, Any]:
        """Get optimization recommendations."""
        return self.cost_tracker.get_optimization_report()

    async def translate_text(
        self,
        text: str,
        target_language: str = "English",
        model_id: Optional[str] = None
    ) -> str:
        """Translate text to target language.

        Args:
            text: Text to translate.
            target_language: Target language name (e.g., "English", "Spanish").
            model_id: Optional model ID to use.

        Returns:
            Translated text.
        """
        prompt = f"Translate the following text to {target_language}. Return only the translation, no extra text.\n\nText: {text}"

        # Use fast model for translation by default as it's a simple task
        result = await self.generate_text(
            prompt=prompt,
            model_id=model_id,
            task_type="generation",
            use_cascading=True
        )

        return result["content"].strip()

    # --- Debate and Verification Methods ---

    def _create_debate_agent(self, role: str) -> 'DebateAgent':
        """Create a debate agent with the specified role.
        
        Args:
            role: Agent role ('analyzer', 'synthesizer', 'curator')
            
        Returns:
            DebateAgent instance
        """
        from ...application.verification.debate_system import DebateAgent, DebateRole
        
        try:
            role_enum = DebateRole(role.lower())
            
            # Determine appropriate tier for role
            if role_enum == DebateRole.ANALYZER:
                tier = ModelTier.SMART  # Highest accuracy
            elif role_enum == DebateRole.SYNTHESIZER:
                tier = ModelTier.MEDIUM  # Balance efficiency/quality
            elif role_enum == DebateRole.CURATOR:
                tier = ModelTier.SMART  # Critical decision making
            else:
                tier = ModelTier.MEDIUM  # Default
            
            return DebateAgent(role_enum, self, tier)
            
        except ValueError:
            logger.error(f"Invalid debate agent role: {role}")
            raise ValueError(f"Role must be one of: {[r.value for r in DebateRole]}")
    
    async def _run_debate_round(self, memory: 'Memory', debate_team: List['DebateAgent']) -> Dict[str, Any]:
        """Run a single debate round between agents.
        
        Args:
            memory: Memory to debate
            debate_team: List of debate agents
            
        Returns:
            Debate result dictionary
        """
        try:
            from ...application.verification.debate_system import DebateSession
            
            # Create debate session
            session = DebateSession(self)
            
            # Run the debate
            result = await session.run_debate(memory)
            
            # Format result for tests
            return {
                "round_id": result.debate_id,
                "participants": [agent.agent_id for agent in result.participating_agents],
                "consensus_score": result.consensus_score,
                "final_decision": result.decision,
                "agent_analyses": [
                    {
                        "agent_id": analysis.agent_id,
                        "agent_role": analysis.agent_role.value,
                        "score": analysis.score,
                        "confidence": analysis.confidence,
                        "reasoning": analysis.reasoning[:200]
                    }
                    for analysis in result.agent_analyses
                ],
                "duration_ms": result.duration_ms,
                "recommendations": result.recommendations
            }
            
        except Exception as e:
            logger.error(f"Debate round failed for memory {memory.id}: {e}")
            return {
                "round_id": f"failed_{memory.id}",
                "participants": [],
                "consensus_score": 0.0,
                "final_decision": "FAILED",
                "error": str(e)
            }
    
    async def _detect_conflicts(self, memories: List['Memory']) -> Dict[str, Any]:
        """Detect conflicts between memories (Consistency Signals).
        
        Args:
            memories: List of memories to check for conflicts
            
        Returns:
            Conflict detection report
        """
        conflicts_found = 0
        conflicting_memories = []
        
        for i, memory1 in enumerate(memories):
            for memory2 in memories[i+1:]:
                if self._detect_contradiction(memory1, memory2):
                    conflicts_found += 1
                    conflicting_memories.append({
                        "memory1_id": memory1.id,
                        "memory2_id": memory2.id,
                        "conflict_type": "contradiction"
                    })
        
        return {
            "conflict_detected": conflicts_found > 0,
            "conflicting_memories": conflicting_memories,
            "total_conflicts": conflicts_found
        }
    
    def _detect_contradiction(self, memory1: 'Memory', memory2: 'Memory') -> bool:
        """Detect contradiction between two memories."""
        content1 = memory1.content.lower().strip()
        content2 = memory2.content.lower().strip()
        
        # Direct contradiction indicators
        opposite_pairs = [
            ("true", "false"), ("false", "true"),
            ("correct", "incorrect"), ("incorrect", "correct"),
            ("yes", "no"), ("no", "yes"),
            ("increase", "decrease"), ("decrease", "increase"),
            ("up", "down"), ("down", "up"),
            ("hot", "cold"), ("cold", "hot")
        ]
        
        for pair in opposite_pairs:
            if pair[0] in content1 and pair[1] in content2:
                return True
            if pair[1] in content1 and pair[0] in content2:
                return True
        
        return False
    
    async def _resolve_conflicts(self, memories: List['Memory']) -> Dict[str, Any]:
        """Resolve conflicts between memories.
        
        Args:
            memories: List of potentially conflicting memories
            
        Returns:
            Conflict resolution recommendations
        """
        # First detect conflicts
        conflicts = await self._detect_conflicts(memories)
        
        # Generate merge suggestions for similar content
        merge_suggestions = []
        for i, memory1 in enumerate(memories):
            for memory2 in memories[i+1:]:
                if not self._detect_contradiction(memory1, memory2):
                    similarity = self._calculate_similarity(memory1.content, memory2.content)
                    if similarity > 0.7:
                        merge_suggestions.append({
                            "memory1_id": memory1.id,
                            "memory2_id": memory2.id, 
                            "similarity": similarity,
                            "recommendation": "merge"
                        })
        
        return {
            **conflicts,
            "merge_suggestions": merge_suggestions
        }
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    async def _run_verification_gate(self, memory: 'Memory') -> Dict[str, Any]:
        """Run verification gate on memory.
        
        Args:
            memory: Memory to verify
            
        Returns:
            Verification result
        """
        try:
            from ...application.verification.verification_gate import create_verification_gate, GateType
            
            # Create verification gate
            gate = create_verification_gate()
            
            # Run standard verification
            result = await gate.verify_memory(memory, GateType.STANDARD)
            
            # Convert to simple format
            return {
                "overall_score": result.final_score,
                "checks_passed": result.checks_passed,
                "checks_failed": result.checks_failed,
                "total_checks": result.checks_executed,
                "verification_id": result.verification_id,
                "recommended_action": result.recommended_action,
                "status": result.final_status
            }
            
        except Exception as e:
            logger.error(f"Verification gate failed for memory {memory.id}: {e}")
            return {
                "overall_score": 0.0,
                "error": str(e)
            }

    # --- Mixture of Thought (MoT) ---
    
    async def generate_mixture_of_thought(
        self,
        prompt: str,
        num_perspectives: int = 3,
        model_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate multiple perspectives and synthesize them (Mixture of Thought).

        This implements the Parallel Extraction strategy (M06.DEV.005) by generating
        multiple reasoning paths with varied parameters and synthesizing the results.
        
        Args:
            prompt: The main prompt or question
            num_perspectives: Number of parallel perspectives to generate
            model_id: Optional specific model to use (defaults to cascading)
            
        Returns:
            Dictionary containing perspectives and synthesized result
        """
        start_time = time.time()
        
        # 1. Generate N responses with high temperature to encourage diversity
        tasks = []
        for i in range(num_perspectives):
            # Vary temperature slightly for each perspective
            perspective_temp = 0.7 + (i * 0.1)
            perspective_prompt = f"Perspective {i+1}: Analyze the following from a unique angle: {prompt}"

            tasks.append(self.generate_text(
                prompt=perspective_prompt,
                model_id=model_id,
                temperature=min(1.0, perspective_temp),
                use_cascading=True
            ))
        
        # Run in parallel
        perspective_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        valid_perspectives = []
        for res in perspective_results:
            if isinstance(res, dict) and 'content' in res:
                valid_perspectives.append(res['content'])
            elif isinstance(res, Exception):
                logger.warning(f"Perspective generation failed: {res}")
        
        if not valid_perspectives:
            raise ValueError("Failed to generate any valid perspectives")
            
        # 2. Synthesize
        synthesis_prompt = f"""
        Analyze the following perspectives on the topic:
        {prompt}
        
        Perspectives:
        {json.dumps(valid_perspectives, indent=2)}
        
        Synthesize a final comprehensive answer that incorporates the best insights from all perspectives.
        Resolve any contradictions and provide a balanced conclusion.
        """
        
        # Use smart model for synthesis
        final_response = await self.generate_text(
            prompt=synthesis_prompt,
            model_id="gemini-2.5-pro", # Use smart model for synthesis
            temperature=0.2, # Low temperature for synthesis
            use_cascading=False
        )
        
        total_time = (time.time() - start_time) * 1000
        
        return {
            "final_response": final_response,
            "perspectives": valid_perspectives,
            "meta": {
                "num_perspectives": len(valid_perspectives),
                "total_time_ms": total_time
            }
        }

    async def analyze_sentiment(
        self,
        text: str,
        model_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze sentiment of text.

        Args:
            text: Text to analyze
            model_id: Optional model ID

        Returns:
            Dictionary with score (-1.0 to 1.0), label, and emotions dict.
        """
        prompt = f"""
        Analyze the sentiment of the following text.
        Return a JSON object with:
        - score: a float between -1.0 (negative) and 1.0 (positive)
        - label: one of "positive", "negative", "neutral", "joy", "anger", "sadness", "fear", "surprise"
        - emotions: a dictionary of specific emotions and their intensity (0.0 to 1.0), e.g., {{"joy": 0.8, "anticipation": 0.2}}

        Text:
        {text}
        """

        response = await self.generate_text(
            prompt=prompt,
            model_id=model_id or "gemini-2.0-flash", # Flash is sufficient for sentiment
            task_type="classification",
            temperature=0.1 # Low temperature for consistent output
        )

        # Parse JSON from response
        try:
            content = response["content"]
            # basic cleanup if markdown code blocks are used
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            return json.loads(content.strip())
        except Exception as e:
            logger.error(f"Failed to parse sentiment analysis response: {e}")
            # Fallback
            return {"score": 0.0, "label": "neutral", "emotions": {}}
    async def generate_structured(
        self,
        prompt: str,
        response_model: Type['T'],
        model_id: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> 'T':
        """Generate structured JSON output validated against a Pydantic model.

        Args:
            prompt: Text prompt
            response_model: Pydantic model class to enforce structure
            model_id: Optional model ID
            temperature: Generation temperature
            max_tokens: Max output tokens

        Returns:
            Instance of response_model populated with generated data
        """
        if not PYDANTIC_AVAILABLE:
            raise ImportError("Pydantic is required for structured output generation")

        # Get JSON schema from Pydantic model
        schema = response_model.model_json_schema()

        # Append instructions to prompt
        structured_prompt = (
            f"{prompt}\n\n"
            f"You must output valid JSON that strictly follows this schema:\n"
            f"```json\n{json.dumps(schema, indent=2)}\n```\n"
            f"Do not include any markdown formatting (like ```json ... ```) in your response, just the raw JSON string."
        )

        # Force lower temperature for deterministic structure
        temp = temperature if temperature is not None else 0.1

        # Call generate_text
        # We assume the model is capable of JSON generation (Gemini Pro/Flash are)
        response = await self.generate_text(
            prompt=structured_prompt,
            model_id=model_id,
            temperature=temp,
            max_tokens=max_tokens,
            task_type="generation",
            use_cascading=True
        )

        content = response["content"].strip()

        # Clean up markdown if present (despite instructions)
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        try:
            json_data = json.loads(content)
            return response_model.model_validate(json_data)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {content[:100]}... Error: {e}")
            raise ValueError(f"LLM failed to generate valid JSON: {e}")
        except Exception as e:
            logger.error(f"Failed to validate response against model: {e}")
            raise ValueError(f"Response validation failed: {e}")


# Example usage helper
async def example_usage():
    """Example of using the GeminiClient with cascading."""
    client = GeminiClient(enable_cascading=True)

    # Simple question - should use fast model
    simple_response = await client.generate_text(
        "What is 2 + 2?",
        use_cascading=True
    )
    print(f"Simple response used {simple_response['model_tier']} tier")

    # Complex analysis - should use smart model
    complex_response = await client.generate_text(
        "Analyze the following code and identify potential security vulnerabilities: /* complex code here */",
        use_cascading=True
    )
    print(f"Complex response used {complex_response['model_tier']} tier")

    # Check budget status
    budget = client.get_budget_status()
    print(f"Budget status: {budget['alert_level']} ({budget['budget_used_percent']:.1f}% used)")

    # Get optimization recommendations
    optimizations = client.get_optimization_report()
    print(f"Optimization opportunities: {len(optimizations['optimizations'])} found")
