"""
Verification gate implementation.

Implements the 6-check verification gate system for memory quality control.
Acts as the main entry point for memory verification processes.
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Callable
from enum import Enum
import logging
from collections import deque

from .self_verification import SelfVerificationLoop, VerificationCheck, VerificationStatus
from .debate_system import DebateSession, DebateResult
from ...domain.memory.entities import Memory
from ...domain.memory.repository import MemoryRepository
from ...infrastructure.gemini.client import GeminiClient


logger = logging.getLogger(__name__)


class GateType(Enum):
    """Types of verification gates."""
    LIGHTWEIGHT = "lightweight"      # Quick verification only
    STANDARD = "standard"           # Self-verification only  
    COMPREHENSIVE = "comprehensive"  # Full verification + debate
    CUSTOM = "custom"               # Custom check configuration


class VerificationResult:
    """Complete verification gate result."""
    
    def __init__(self, memory_id: str, gate_type: GateType):
        self.memory_id = memory_id
        self.gate_type = gate_type
        self.verification_id = f"gate_{memory_id}_{int(datetime.now(timezone.utc).timestamp())}"
        self.start_time = datetime.now(timezone.utc)
        
        # Results storage
        self.self_verification_result: Optional[Dict[str, Any]] = None
        self.debate_result: Optional[DebateResult] = None
        
        # Final assessment
        self.final_score: float = 0.0
        self.final_status: str = VerificationStatus.PENDING.value
        self.confidence_level: float = 0.0
        self.recommended_action: str = "none"
        
        # Tracking
        self.total_duration_ms: float = 0.0
        self.checks_executed: int = 0
        self.checks_passed: int = 0
        self.checks_failed: int = 0
        self.errors: List[str] = []
        
    def calculate_final(self):
        """Calculate final verification results."""
        end_time = datetime.now(timezone.utc)
        self.total_duration_ms = (end_time - self.start_time).total_seconds() * 1000
        
        # If self-verification was performed, use its results
        if self.self_verification_result:
            score = self.self_verification_result.get('overall_score', 0.0)
            
            # If debate was also performed, combine results
            if self.debate_result:
                debate_score = self.debate_result.final_score
                debate_confidence = self.debate_result.confidence_level
                
                # Weight debate more heavily when confidence is high
                if debate_confidence >= 0.7:
                    self.final_score = score * 0.4 + debate_score * 0.6
                else:
                    self.final_score = score * 0.7 + debate_score * 0.3
                
                self.confidence_level = (score + debate_confidence) / 2
                
            else:
                self.final_score = score
                self.confidence_level = score * 0.9  # Account for lack of cross-verification
            
            # Extract check statistics
            self.checks_executed = len(self.self_verification_result.get('checks', []))
            self.checks_passed = self.self_verification_result.get('passed_checks', 0)
            self.checks_failed = self.self_verification_result.get('failed_checks', 0)
        
        # Only debate was performed
        elif self.debate_result:
            self.final_score = self.debate_result.final_score
            self.confidence_level = self.debate_result.confidence_level
        
        # No verification performed
        else:
            self.final_score = 0.0
            self.confidence_level = 0.0
            self.errors.append("No verification checks were executed")
        
        # Determine final status
        self.final_status = self._determine_final_status()
        
        # Determine recommended action
        self.recommended_action = self._determine_recommended_action()
    
    def _determine_final_status(self) -> str:
        """Determine final verification status."""
        # High confidence and score
        if self.final_score >= 0.8 and self.confidence_level >= 0.7:
            return VerificationStatus.PASSED.value
        
        # Moderate confidence and score
        elif self.final_score >= 0.6 and self.confidence_level >= 0.5:
            return VerificationStatus.NEEDS_REVIEW.value
        
        # Low confidence or score
        elif self.final_score < 0.4 or self.confidence_level < 0.3:
            return VerificationStatus.FAILED.value
        
        # Borderline cases
        else:
            return VerificationStatus.NEEDS_REVIEW.value
    
    def _determine_recommended_action(self) -> str:
        """Determine recommended action based on verification."""
        if self.final_status == VerificationStatus.PASSED.value:
            return "accept"
        elif self.final_status == VerificationStatus.FAILED.value:
            return "reject"
        elif self.final_score >= 0.7:
            return "minor_refinement"  
        elif self.final_score >= 0.5:
            return "major_refinement"
        else:
            return "reprocess"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "verification_id": self.verification_id,
            "memory_id": self.memory_id,
            "gate_type": self.gate_type.value,
            "start_time": self.start_time.isoformat(),
            "final_score": self.final_score,
            "final_status": self.final_status,
            "confidence_level": self.confidence_level,
            "recommended_action": self.recommended_action,
            "total_duration_ms": self.total_duration_ms,
            "checks_executed": self.checks_executed,
            "checks_passed": self.checks_passed,
            "checks_failed": self.checks_failed,
            "has_self_verification": self.self_verification_result is not None,
            "has_debate_result": self.debate_result is not None,
            "errors": self.errors,
            "self_verification": self.self_verification_result,
            "debate_result": self.debate_result.__dict__ if self.debate_result else None
        }


class VerificationGate:
    """Main verification gate coordinator."""
    
    def __init__(self, 
                 repository: Optional[MemoryRepository] = None,
                 gemini_client: Optional[GeminiClient] = None,
                 verification_loop: Optional[SelfVerificationLoop] = None):
        self.client = gemini_client or GeminiClient()
        self.verification_loop = verification_loop or SelfVerificationLoop(self.client)
        self.repository = repository

        # Auto-initialize repository if not provided (Best Effort)
        if not self.repository:
            try:
                from ...infrastructure.surrealdb.client import SurrealDBClient
                from ...infrastructure.persistence.surrealdb_repository import SurrealDBMemoryRepository
                # This will use env vars via SurrealConfig logic
                self.repository = SurrealDBMemoryRepository(SurrealDBClient())
            except Exception as e:
                logger.warning(f"Could not initialize default repository: {e}")
        
        # Configuration
        self.default_gate_type = GateType.STANDARD
        self.debate_threshold = 0.7  # Trigger debate for high-importance memories
        
        # Performance tracking (Bounded to prevent leak)
        self.verification_history: deque = deque(maxlen=1000)
    
    async def verify_memory(self, 
                          memory: Memory, 
                          gate_type: Optional[GateType] = None,
                          context: Optional[Dict[str, Any]] = None) -> VerificationResult:
        """Run verification gate on memory."""
        gate_type = gate_type or self.default_gate_type
        result = VerificationResult(memory.id, gate_type)
        
        logger.info(f"Starting verification gate {gate_type.value} for memory {memory.id}")
        
        try:
            # Determine verification approach based on gate type
            if gate_type == GateType.LIGHTWEIGHT:
                await self._run_lightweight_verification(memory, result, context)
            elif gate_type == GateType.STANDARD:
                await self._run_standard_verification(memory, result, context)
            elif gate_type == GateType.COMPREHENSIVE:
                await self._run_comprehensive_verification(memory, result, context)
            elif gate_type == GateType.CUSTOM:
                await self._run_custom_verification(memory, result, context)
            else:
                raise ValueError(f"Unsupported gate type: {gate_type}")
            
            # Calculate final results
            result.calculate_final()
            
            # Track verification
            self.verification_history.append(result)
            
            # Update memory verification status
            await self._update_memory_verification(memory, result)
            
            logger.info(f"Verification gate completed for memory {memory.id}: "
                       f"Score={result.final_score:.3f}, Status={result.final_status}")
            
            return result
            
        except Exception as e:
            logger.error(f"Verification gate failed for memory {memory.id}: {e}")
            result.errors.append(str(e))
            result.calculate_final()  # Still calculate partial results
            return result
    
    async def _run_lightweight_verification(self, memory: Memory, result: VerificationResult, 
                                           context: Optional[Dict[str, Any]]):
        """Run lightweight verification (subset of checks only)."""
        # Only run most critical checks
        lightweight_checks = [
            "factual_accuracy",
            "consistency"
        ]
        
        # Modify verification loop to run only specified checks
        original_checks = self.verification_loop.verification_checks
        self.verification_loop.verification_checks = [
            check for check in original_checks 
            if check.name in lightweight_checks
        ]
        
        try:
            result.self_verification_result = await self.verification_loop.verify_memory(memory, context)
        finally:
            # Restore original checks
            self.verification_loop.verification_checks = original_checks
    
    async def _run_standard_verification(self, memory: Memory, result: VerificationResult, 
                                       context: Optional[Dict[str, Any]]):
        """Run standard self-verification only."""
        result.self_verification_result = await self.verification_loop.verify_memory(memory, context)
    
    async def _run_comprehensive_verification(self, memory: Memory, result: VerificationResult, 
                                            context: Optional[Dict[str, Any]]):
        """Run comprehensive verification (self-verification + debate)."""
        # First run self-verification
        result.self_verification_result = await self.verification_loop.verify_memory(memory, context)
        
        # Determine if debate is needed based on memory importance and self-verification score
        self_verification_score = result.self_verification_result.get('overall_score', 0.0)
        memory_importance = memory.importance_score.value
        
        should_run_debate = (
            memory_importance >= self.debate_threshold or 
            self_verification_score < 0.7 or
            result.self_verification_result.get('result') == 'FAILED'
        )
        
        if should_run_debate:
            debate_session = DebateSession(self.client)
            result.debate_result = await debate_session.run_debate(memory, context)
        else:
            logger.debug(f"Skipping debate for memory {memory.id} - self-verification score {self_verification_score:.3f} sufficient")
    
    async def _run_custom_verification(self, memory: Memory, result: VerificationResult,
                                       context: Optional[Dict[str, Any]]):
        """Run custom verification based on context configuration."""
        config = context.get('verification_config', {})
        
        # Support for custom check selection
        custom_checks = config.get('checks')
        if custom_checks and isinstance(custom_checks, list):
            original_checks = self.verification_loop.verification_checks
            self.verification_loop.verification_checks = [
                check for check in original_checks 
                if check.name in custom_checks
            ]
            
            try:
                result.self_verification_result = await self.verification_loop.verify_memory(memory, context)
            finally:
                self.verification_loop.verification_checks = original_checks
        else:
            # Fallback to standard verification
            await self._run_standard_verification(memory, result, context)
        
        # Custom debate configuration
        if config.get('include_debate', False):
            debate_session = DebateSession(self.client)
            result.debate_result = await debate_session.run_debate(memory, context)
    
    async def batch_verify_memories(self, 
                                  memories: List[Memory], 
                                  gate_type: Optional[GateType] = None,
                                  context: Optional[Dict[str, Any]] = None) -> List[VerificationResult]:
        """Run verification gate on multiple memories concurrently."""
        logger.info(f"Starting batch verification for {len(memories)} memories")
        
        # Create verification tasks
        verification_tasks = [
            self.verify_memory(memory, gate_type, context or {})
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
                failed_result = VerificationResult(memories[i].id, gate_type or self.default_gate_type)
                failed_result.errors.append(str(result))
                failed_result.calculate_final()
                valid_results.append(failed_result)
            else:
                valid_results.append(result)
        
        logger.info(f"Batch verification completed: {len(valid_results)} results")
        
        return valid_results
    
    async def update_verification_gate_config(self, config: Dict[str, Any]):
        """Update verification gate configuration."""
        if 'default_gate_type' in config:
            self.default_gate_type = GateType(config['default_gate_type'])
        
        if 'debate_threshold' in config:
            self.debate_threshold = config['debate_threshold']
        
        logger.info("Verification gate configuration updated")
    
    async def _update_memory_verification(self, memory: Memory, result: VerificationResult):
        """Update memory with verification result."""
        if not self.repository:
            logger.warning("Skipping database update: No repository available.")
            return

        try:
            # Update memory fields locally
            memory.verification_count += 1
            memory.verification_status = result.final_status
            memory.verified_at = datetime.now(timezone.utc)
            
            # Store verification score if supported
            if hasattr(memory, 'verification_score'):
                memory.verification_score = result.final_score
            
            # Persist to database
            # Note: We update the whole object which is safe/idempotent in our architecture
            await self.repository.update(memory)
            
        except Exception as e:
            logger.warning(f"Failed to update memory verification in database: {e}")
    
    def get_verification_stats(self, limit: int = 100) -> Dict[str, Any]:
        """Get verification gate performance statistics."""
        if not self.verification_history:
            return {"total_verified": 0}
        
        # Filter for recent verifications
        recent_history = list(self.verification_history)[-limit:]
        
        # Calculate statistics
        total_verified = len(recent_history)
        passed_count = len([r for r in recent_history if r.final_status == VerificationStatus.PASSED.value])
        failed_count = len([r for r in recent_history if r.final_status == VerificationStatus.FAILED.value])
        needs_review_count = len([r for r in recent_history if r.final_status == VerificationStatus.NEEDS_REVIEW.value])
        
        # Score distribution
        scores = [r.final_score for r in recent_history]
        average_score = sum(scores) / len(scores) if scores else 0.0
        
        # Confidence distribution
        confidences = [r.confidence_level for r in recent_history]
        average_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        # Performance metrics
        durations = [r.total_duration_ms for r in recent_history if r.total_duration_ms > 0]
        average_duration_ms = sum(durations) / len(durations) if durations else 0.0
        
        return {
            "total_verified": total_verified,
            "status_distribution": {
                "passed": passed_count,
                "failed": failed_count,
                "needs_review": needs_review_count
            },
            "score_statistics": {
                "average": average_score,
                "min": min(scores) if scores else 0.0,
                "max": max(scores) if scores else 0.0
            },
            "confidence_statistics": {
                "average": average_confidence,
                "min": min(confidences) if confidences else 0.0,
                "max": max(confidences) if confidences else 0.0
            },
            "performance_statistics": {
                "average_duration_ms": average_duration_ms,
                "checks_per_verification": sum(r.checks_executed for r in recent_history) / total_verified if total_verified > 0 else 0.0
            },
            "gate_type_distribution": {
                gate_type.value: len([r for r in recent_history if r.gate_type == gate_type])
                for gate_type in GateType
            }
        }
    
    def get_recent_verifications(self, memory_id: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent verification results."""
        verifications = list(self.verification_history)[-limit:]
        
        if memory_id:
            verifications = [v for v in verifications if v.memory_id == memory_id]
        
        return [v.to_dict() for v in verifications]


# Factory function for easy initialization
def create_verification_gate(gemini_api_key: Optional[str] = None,
                            gate_type: Optional[GateType] = None) -> VerificationGate:
    """Create a configured verification gate."""
    client = GeminiClient(api_key=gemini_api_key) if gemini_api_key else GeminiClient()
    return VerificationGate(gemini_client=client)
