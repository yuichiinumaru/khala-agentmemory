"""
Self-verification loop implementation for KHALA memory system.

Implements comprehensive self-reflection and quality assurance mechanisms
following the 6-check verification framework.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
import logging

from ...domain.memory.entities import Memory, MemoryTier
from ...domain.memory.value_objects import ImportanceScore, DecayScore
from ...infrastructure.gemini.client import GeminiClient
from ...infrastructure.gemini.models import ModelRegistry, ModelTier
from ..verification.debate_system import DebateSession, DebateAgent


logger = logging.getLogger(__name__)


class VerificationStatus(Enum):
    """Verification status types."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PASSED = "passed"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"


class VerificationCheck:
    """Individual verification check implementation."""
    
    def __init__(self, name: str, weight: float, threshold: float = 0.7):
        self.name = name
        self.weight = weight
        self.threshold = threshold
        self.last_run = None
        self.last_score = None
    
    async def execute(self, memory: Memory, context: Dict[str, Any]) -> float:
        """Execute the verification check."""
        raise NotImplementedError("Subclasses must implement execute method")


class FactualAccuracyCheck(VerificationCheck):
    """Check factual accuracy of memory content."""
    
    def __init__(self):
        super().__init__("factual_accuracy", weight=0.30, threshold=0.8)
        self.client = None
    
    async def execute(self, memory: Memory, context: Dict[str, Any]) -> float:
        """Verify factual accuracy using LLM analysis."""
        if not self.client:
            self.client = GeminiClient()
        
        prompt = f"""
        Analyze the factual accuracy of this memory statement:
        
        Memory: {memory.content}
        Source: {memory.metadata.get('source', 'unknown')}
        Confidence: {memory.metadata.get('confidence', 'unknown')}
        
        Rate the factual accuracy on a scale of 0.0 to 1.0 where:
        - 1.0 = Completely accurate and verifiable
        - 0.8 = Highly accurate with minor uncertainties
        - 0.6 = Generally accurate but some concerns
        - 0.4 = Partially accurate, significant issues
        - 0.2 = Mostly inaccurate
        - 0.0 = Completely inaccurate
        
        Respond with just the numerical score (0.0-1.0).
        """
        
        try:
            response = await self.client.generate_text(
                prompt, 
                use_caching=True,
                model_id="gemini-3-pro-preview"
            )
            
            score = float(response['content'].strip())
            self.last_score = max(0.0, min(1.0, score))
            self.last_run = datetime.now(timezone.utc)
            
            return self.last_score
            
        except Exception as e:
            logger.warning(f"Factual accuracy check failed for memory {memory.id}: {e}")
            return 0.5  # Default to medium confidence on failure


class ConsistencyCheck(VerificationCheck):
    """Check consistency with existing memories."""
    
    def __init__(self):
        super().__init__("consistency", weight=0.20, threshold=0.7)
    
    async def execute(self, memory: Memory, context: Dict[str, Any]) -> float:
        """Verify consistency with related memories."""
        related_memories = context.get('related_memories', [])
        
        if not related_memories:
            return 1.0  # No conflicts if no related memories
        
        contradictions_found = 0
        total_comparisons = len(related_memories)
        
        for related_memory in related_memories:
            if self._detect_contradiction(memory, related_memory):
                contradictions_found += 1
        
        # Score inversely proportional to contradictions found
        consistency_score = 1.0 - (contradictions_found / total_comparisons) if total_comparisons > 0 else 1.0
        
        self.last_score = consistency_score
        self.last_run = datetime.now(timezone.utc)
        
        return consistency_score
    
    def _detect_contradiction(self, memory1: Memory, memory2: Memory) -> bool:
        """Simple contradiction detection based on semantic similarity."""
        # This would be enhanced with more sophisticated NLP in production
        content1 = memory1.content.lower().strip()
        content2 = memory2.content.lower().strip()
        
        # Direct contradiction indicators
        contradiction_words = ["not", "never", "incorrect", "wrong", "false"]
        
        for word in contradiction_words:
            if word in content1 and word in content2:
                continue  # Both have negation, need deeper analysis
        
        # Simple heuristic: if content is similar but key facts differ
        similarity = self._calculate_similarity(content1, content2)
        
        if similarity > 0.8:  # High similarity suggests same topic
            # Check for opposite statements
            opposite_pairs = [
                ("true", "false"),
                ("correct", "incorrect"),
                ("yes", "no"),
                ("increase", "decrease"),
                ("up", "down"),
                ("hot", "cold")
            ]
            
            for pair in opposite_pairs:
                if pair[0] in content1 and pair[1] in content2:
                    return True
                if pair[1] in content1 and pair[0] in content2:
                    return True
        
        return False
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Simple similarity calculation."""
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0


class RelevanceCheck(VerificationCheck):
    """Check relevance and importance of memory."""
    
    def __init__(self):
        super().__init__("relevance", weight=0.15, threshold=0.6)
    
    async def execute(self, memory: Memory, context: Dict[str, Any]) -> float:
        """Verify memory relevance and importance."""
        # Use existing importance score as base
        base_importance = memory.importance_score.value
        
        # Adjust for recency if specified in context
        recency_modifier = 1.0
        if 'user_preferences' in context:
            preferences = context['user_preferences']
            if 'recent_topics' in preferences:
                for topic in preferences['recent_topics']:
                    if topic.lower() in memory.content.lower():
                        recency_modifier = 1.2
                        break
        
        # Calculate final relevance score
        final_score = min(1.0, base_importance * recency_modifier)
        
        self.last_score = final_score
        self.last_run = datetime.now(timezone.utc)
        
        return final_score


class FreshnessCheck(VerificationCheck):
    """Check temporal freshness of memory."""
    
    def __init__(self):
        super().__init__("freshness", weight=0.10, threshold=0.5)
    
    async def execute(self, memory: Memory, context: Dict[str, Any]) -> float:
        """Verify memory freshness based on age and expected obsolescence."""
        now = datetime.now(timezone.utc)
        age_days = (now - memory.created_at).days
        
        # Base score from decay calculation
        base_freshness = memory.decay_score.value
        
        # Adjust based on memory tier expectations
        if memory.tier == MemoryTier.WORKING:
            # Working memories should be very fresh
            expected_max_age = 1  # 1 day
            age_factor = max(0.0, 1.0 - (age_days / expected_max_age))
            final_score = min(1.0, base_freshness + age_factor)
            
        elif memory.tier == MemoryTier.SHORT_TERM:
            # Short-term memories can be older
            expected_max_age = 15  # 15 days
            age_factor = max(0.0, 1.0 - (age_days / expected_max_age))
            final_score = min(1.0, base_freshness + age_factor)
            
        else:  # LONG_TERM
            # Long-term memories have less strict freshness requirements
            final_score = base_freshness
        
        self.last_score = final_score
        self.last_run = datetime.now(timezone.utc)
        
        return final_score


class CompletenessCheck(VerificationCheck):
    """Check completeness of memory information."""
    
    def __init__(self):
        super().__init__("completeness", weight=0.10, threshold=0.6)
    
    async def execute(self, memory: Memory, context: Dict[str, Any]) -> float:
        """Verify memory has sufficient supporting information."""
        completeness_score = 0.0
        total_checks = 6
        
        # Check content length (should be substantial)
        if len(memory.content) > 50:
            completeness_score += 1
        
        # Check for source information
        if memory.metadata.get('source'):
            completeness_score += 1
        
        # Check for confidence indicators
        if 'confidence' in memory.metadata:
            completeness_score += 1
        
        # Check for related entities
        if len(memory.related_entities) > 0:
            completeness_score += 1
        
        # Check for relationships
        if len(memory.relationships) > 0:
            completeness_score += 1
        
        # Check for verification history
        if memory.verification_count > 0:
            completeness_score += 1
        
        final_score = completeness_score / total_checks
        
        self.last_score = final_score
        self.last_run = datetime.now(timezone.utc)
        
        return final_score


class AuthenticityCheck(VerificationCheck):
    """Check authenticity and source credibility."""
    
    def __init__(self):
        super().__init__("authenticity", weight=0.15, threshold=0.7)
        self.client = None
    
    async def execute(self, memory: Memory, context: Dict[str, Any]) -> float:
        """Verify authenticity based on source and content analysis."""
        authenticity_score = 0.0
        
        # Check source credibility
        source = memory.metadata.get('source', '').lower()
        credible_sources = [
            "peer_reviewed", "academic", "scientific", "official",
            "government", "research", "study", "publication"
        ]
        
        if any(cred in source for cred in credible_sources):
            authenticity_score += 0.4
        
        # Check for specific evidence indicators
        evidence_words = [
            "according to", "research shows", "study found", "data indicates",
            "evidence suggests", "results demonstrate", "analysis reveals"
        ]
        
        content_lower = memory.content.lower()
        evidence_count = sum(1 for word in evidence_words if word in content_lower)
        if evidence_count >= 2:
            authenticity_score += 0.3
        
        # Check confidence indicators
        confidence = memory.metadata.get('confidence')
        if confidence:
            try:
                conf_value = float(confidence)
                if conf_value >= 0.8:
                    authenticity_score += 0.3
                elif conf_value >= 0.6:
                    authenticity_score += 0.2
                elif conf_value >= 0.4:
                    authenticity_score += 0.1
            except (ValueError, TypeError):
                pass
        
        self.last_score = min(1.0, authenticity_score)
        self.last_run = datetime.now(timezone.utc)
        
        return self.last_score


class SelfVerificationLoop:
    """Main self-verification loop coordinator."""
    
    def __init__(self, gemini_client: Optional[GeminiClient] = None):
        self.client = gemini_client or GeminiClient()
        
        # Initialize all verification checks
        self.verification_checks = [
            FactualAccuracyCheck(),
            ConsistencyCheck(),
            RelevanceCheck(),
            FreshnessCheck(),
            CompletenessCheck(),
            AuthenticityCheck()
        ]
        
        # Verification state tracking
        self.verification_history: Dict[str, List[Dict[str, Any]]] = {}
        
    async def verify_memory(self, memory: Memory, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Run complete verification loop on a memory."""
        logger.info(f"Starting verification for memory {memory.id}")
        
        context = context or {}
        start_time = datetime.now(timezone.utc)
        
        # Execute all verification checks
        check_results = []
        overall_score = 0.0
        
        for check in self.verification_checks:
            try:
                logger.debug(f"Executing check: {check.name}")
                score = await check.execute(memory, context)
                weighted_score = score * check.weight
                
                check_result = {
                    "name": check.name,
                    "score": score,
                    "weighted_score": weighted_score,
                    "weight": check.weight,
                    "threshold": check.threshold,
                    "passed": score >= check.threshold
                }
                
                check_results.append(check_result)
                overall_score += weighted_score
                
                logger.debug(f"Check {check.name}: {score:.3f} (threshold: {check.threshold})")
                
            except Exception as e:
                logger.error(f"Verification check {check.name} failed: {e}")
                # Failed checks get minimum score
                check_results.append({
                    "name": check.name,
                    "score": 0.0,
                    "weighted_score": 0.0,
                    "weight": check.weight,
                    "threshold": check.threshold,
                    "passed": False,
                    "error": str(e)
                })
        
        # Determine overall verification result
        verification_result = self._determine_result(overall_score, check_results)
        
        # Update memory verification metadata
        await self._update_memory_verification(memory, verification_result)
        
        # Record in history
        await self._record_verification_history(memory.id, verification_result)
        
        # Calculate verification duration
        end_time = datetime.now(timezone.utc)
        verification_duration_ms = (end_time - start_time).total_seconds() * 1000
        
        final_result = {
            "memory_id": memory.id,
            "verification_id": f"verif_{memory.id}_{int(start_time.timestamp())}",
            "timestamp": start_time.isoformat(),
            "overall_score": overall_score,
            "verification_duration_ms": verification_duration_ms,
            "result": verification_result,
            "checks": check_results,
            "passed_checks": len([c for c in check_results if c["passed"]]),
            "failed_checks": len([c for c in check_results if not c["passed"]]),
            "recommended_action": self._get_recommended_action(overall_score, check_results)
        }
        
        logger.info(f"Verification completed for memory {memory.id}: "
                   f"Score={overall_score:.3f}, Result={verification_result}")
        
        return final_result
    
    def _determine_result(self, overall_score: float, check_results: List[Dict]) -> str:
        """Determine verification result based on scores."""
        passed_checks = len([c for c in check_results if c["passed"]])
        total_checks = len(check_results)
        
        # Strict criteria: all critical checks must pass
        critical_checks = ["factual_accuracy", "consistency"]
        failed_critical = any(
            not c["passed"] for c in check_results 
            if c["name"] in critical_checks
        )
        
        if failed_critical:
            return "FAILED"
        
        # High confidence result
        if overall_score >= 0.85 and passed_checks == total_checks:
            return "PASSED"
        
        # Medium confidence with minor issues
        if overall_score >= 0.7 and passed_checks >= total_checks - 1:
            return "NEEDS_REVIEW"
        
        # Low confidence or multiple failures
        if overall_score < 0.5 or passed_checks < total_checks // 2:
            return "FAILED"
        
        return "NEEDS_REVIEW"
    
    def _get_recommended_action(self, overall_score: float, check_results: List[Dict]) -> str:
        """Get recommended action based on verification results."""
        failed_checks = [c["name"] for c in check_results if not c["passed"]]
        
        if overall_score >= 0.85 and not failed_checks:
            return "accept"
        elif overall_score >= 0.7 and len(failed_checks) <= 1:
            return "minor_refinement"
        elif "factual_accuracy" in failed_checks or "consistency" in failed_checks:
            return "major_revision"
        else:
            return "reject"
    
    async def _update_memory_verification(self, memory: Memory, verification_result: str):
        """Update memory with verification metadata."""
        memory.verification_count += 1
        memory.verification_status = verification_result
        memory.verified_at = datetime.now(timezone.utc)
        
        # Update verification score
        if hasattr(memory, 'verification_score'):
            memory.verification_score = verification_result
        
        # Import database operations
        try:
            from ...infrastructure.surrealdb.client import SurrealDBClient
            db_client = SurrealDBClient()
            
            await db_client.update_memory(
                memory_id=memory.id,
                updates={
                    "verification_count": memory.verification_count,
                    "verification_status": memory.verification_status,
                    "verified_at": memory.verified_at.isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            )
        except Exception as e:
            logger.warning(f"Failed to update memory verification in database: {e}")
    
    async def _record_verification_history(self, memory_id: str, result: Dict[str, Any]):
        """Record verification in history log."""
        if memory_id not in self.verification_history:
            self.verification_history[memory_id] = []
        
        self.verification_history[memory_id].append({
            "timestamp": result["timestamp"],
            "overall_score": result["overall_score"],
            "result": result["result"],
            "verification_id": result["verification_id"]
        })
        
        # Keep only last 10 verification records per memory
        if len(self.verification_history[memory_id]) > 10:
            self.verification_history[memory_id] = self.verification_history[memory_id][-10:]
    
    async def get_verification_history(self, memory_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get verification history for a memory."""
        history = self.verification_history.get(memory_id, [])
        return history[-limit:] if limit > 0 else history
    
    async def batch_verify_memories(self, memories: List[Memory], context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Run verification on multiple memories concurrently."""
        logger.info(f"Starting batch verification for {len(memories)} memories")
        
        # Create verification tasks
        verification_tasks = [
            self.verify_memory(memory, context or {}) 
            for memory in memories
        ]
        
        # Execute all verifications concurrently
        if len(verification_tasks) > 0:
            results = await asyncio.gather(*verification_tasks, return_exceptions=True)
        else:
            results = []
        
        # Handle any exceptions in batch
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Batch verification failed for memory {memories[i].id}: {result}")
                valid_results.append({
                    "memory_id": memories[i].id,
                    "error": str(result),
                    "result": "FAILED"
                })
            else:
                valid_results.append(result)
        
        logger.info(f"Batch verification completed: {len(valid_results)} results")
        
        return valid_results
    
    def get_verification_stats(self, memory_id: Optional[str] = None) -> Dict[str, Any]:
        """Get verification statistics."""
        total_verifications = sum(len(history) for history in self.verification_history.values())
        
        # Calculate averages
        all_scores = []
        result_counts = {"PASSED": 0, "FAILED": 0, "NEEDS_REVIEW": 0}
        
        for memory_id, history in self.verification_history.items():
            for record in history:
                all_scores.append(record["overall_score"])
                result_counts[record["result"]] += 1
        
        avg_score = sum(all_scores) / len(all_scores) if all_scores else 0.0
        
        stats = {
            "total_verifications": total_verifications,
            "average_score": avg_score,
            "result_distribution": result_counts,
            "memories_verified": len(self.verification_history)
        }
        
        if memory_id and memory_id in self.verification_history:
            memory_history = self.verification_history[memory_id]
            memory_scores = [r["overall_score"] for r in memory_history]
            
            stats[memory_id] = {
                "verification_count": len(memory_history),
                "average_score": sum(memory_scores) / len(memory_scores) if memory_scores else 0.0,
                "latest_result": memory_history[-1]["result"] if memory_history else None,
                "last_verified": memory_history[-1]["timestamp"] if memory_history else None
            }
        
        return stats


# Factory function for easy initialization
def create_verification_loop(gemini_api_key: Optional[str] = None) -> SelfVerificationLoop:
    """Create a configured verification loop."""
    client = GeminiClient(api_key=gemini_api_key) if gemini_api_key else GeminiClient()
    return SelfVerificationLoop(client)
