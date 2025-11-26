"""
Multi-agent debate system for memory verification.

Implements a 3-agent consensus system (Analyzer, Synthesizer, Curator)
for robust memory verification and quality assurance.
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
import logging
from dataclasses import dataclass

from ...infrastructure.gemini.client import GeminiClient
from ...infrastructure.gemini.models import ModelRegistry, ModelTier
from ...domain.memory.entities import Memory


logger = logging.getLogger(__name__)


class DebateRole(Enum):
    """Agent roles in debate system."""
    ANALYZER = "analyzer"
    SYNTHESIZER = "synthesizer"
    CURATOR = "curator"


class DebateStatus(Enum):
    """Debate session status."""
    INITIALIZING = "initializing"
    IN_PROGRESS = "in_progress"
    CONSENSUS_REACHED = "consensus_reached"
    NO_CONSENSUS = "no_consensus"
    FAILED = "failed"


@dataclass
class AgentAnalysis:
    """Analysis result from a debate agent."""
    agent_id: str
    agent_role: DebateRole
    score: float
    confidence: float
    reasoning: str
    timestamp: datetime
    metadata: Dict[str, Any]


@dataclass
class DebateResult:
    """Final result of debate session."""
    debate_id: str
    memory_id: str
    final_score: float
    confidence_level: float
    decision: str
    participating_agents: List[str]
    agent_analyses: List[AgentAnalysis]
    consensus_score: float
    duration_ms: float
    recommendations: List[str]
    timestamp: datetime


class DebateAgent:
    """Individual debate agent with specialized role."""
    
    def __init__(self, role: DebateRole, client: GeminiClient, tier: ModelTier):
        self.role = role
        self.client = client
        self.tier = tier
        self.agent_id = f"debate_{role.value}_{datetime.now(timezone.utc).strftime('%H%M%S')}"
        
        # Role-specific prompts
        self.prompts = self._get_role_prompts()
        
        # Performance tracking
        self.total_analyses = 0
        self.average_confidence = 0.0
        
    def _get_role_prompts(self) -> Dict[str, str]:
        """Get role-specific system prompts."""
        base_prompt = "You are a specialized AI agent participating in a multi-agent debate to verify memory quality. "
        
        role_prompts = {
            DebateRole.ANALYZER: base_prompt + """
            Your role is ANALYZER. Focus on:
            1. Factual accuracy verification
            2. Logical consistency checking  
            3. Evidence evaluation
            4. Source credibility assessment
            5. Potential bias identification
            
            Provide detailed analysis with specific scores (0.0-1.0) for:
            - factual_score: accuracy of claims
            - logical_score: internal consistency  
            - evidence_score: quality of supporting evidence
            - bias_score: presence of bias (lower is better)
            - overall_score: combined weighted assessment
            
            Format response as JSON with these fields and include brief reasoning.
            """,
            
            DebateRole.SYNTHESIZER: base_prompt + """
            Your role is SYNTHESIZER. Focus on:
            1. Integrating analyses from multiple perspectives
            2. Identifying patterns and commonalities
            3. Resolving conflicts between different analyses
            4. Building consensus across viewpoints
            5. Generating balanced recommendations
            
            Consider all provided agent analyses and provide:
            - consensus_score: level of agreement between analyses (0.0-1.0)
            - conflict_areas: areas where agents disagree
            - synthesis_quality: quality of integration (0.0-1.0)
            - actionability: clarity of recommendations (0.0-1.0)
            - overall_score: synthesized assessment (0.0-1.0)
            
            Format response as JSON with these fields and explain reasoning.
            """,
            
            DebateRole.CURATOR: base_prompt + """
            Your role is CURATOR. Focus on:
            1. Final quality gatekeeping
            2. Risk assessment and mitigation
            3. Long-term value evaluation
            4. Compliance and safety checking
            5. Trustworthiness validation
            
            Based on all prior analyses, make final decisions about:
            - trustworthiness_score: overall trust in the memory (0.0-1.0)
            - risk_level: low/medium/high assessment
            - retention_priority: importance for long-term storage (0.0-1.0)
            - action_required: any actions needed (none/minor/major/reject)
            - final_recommendation: accept/refine/reject with confidence (0.0-1.0)
            
            Format response as JSON with these fields and justify your decision.
            """
        }
        
        return role_prompts.get(self.role, base_prompt)
    
    async def analyze_memory(self, memory: Memory, context: Dict[str, Any], 
                           prior_analyses: Optional[List[AgentAnalysis]] = None) -> AgentAnalysis:
        """Analyze memory based on agent role."""
        start_time = datetime.now(timezone.utc)
        
        # Prepare analysis prompt
        analysis_prompt = self._prepare_analysis_prompt(memory, context, prior_analyses)
        
        try:
            # Generate analysis using appropriate model tier
            model = ModelRegistry.get_model_by_tier(self.tier)
            
            response = await self.client.generate_text(
                f"{self.prompts[self.role]}\n\n{analysis_prompt}",
                use_caching=True,
                model_id=model.model_id
            )
            
            # Parse response to extract scores
            scores = self._parse_analysis_response(response['content'])
            
            # Calculate confidence based on response coherence
            confidence = self._calculate_confidence(response['content'], scores)
            
            # Create analysis result
            analysis = AgentAnalysis(
                agent_id=self.agent_id,
                agent_role=self.role,
                score=scores.get('overall_score', 0.5),
                confidence=confidence,
                reasoning=response['content'][:500],  # Truncate for storage
                timestamp=start_time,
                metadata={
                    "model_used": model.model_id,
                    "tier": self.tier.value,
                    "detailed_scores": scores,
                    "response_time_ms": (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                }
            )
            
            # Update performance tracking
            self.total_analyses += 1
            self.average_confidence = (self.average_confidence * (self.total_analyses - 1) + confidence) / self.total_analyses
            
            return analysis
            
        except Exception as e:
            logger.error(f"Analysis failed for {self.role.value} agent {self.agent_id}: {e}")
            
            # Return fallback analysis
            return AgentAnalysis(
                agent_id=self.agent_id,
                agent_role=self.role,
                score=0.5,  # Default neutral score
                confidence=0.0,  # No confidence in failed analysis
                reasoning=f"Analysis failed: {str(e)}",
                timestamp=start_time,
                metadata={"error": str(e), "fallback": True}
            )
    
    def _prepare_analysis_prompt(self, memory: Memory, context: Dict[str, Any], 
                               prior_analyses: Optional[List[AgentAnalysis]]) -> str:
        """Prepare comprehensive analysis prompt."""
        prompt = f"""
        Memory ID: {memory.id}
        Content: {memory.content}
        Importance Score: {memory.importance_score.value}
        Memory Tier: {memory.tier.value}
        Created: {memory.created_at.isoformat()}
        
        Metadata:
        """
        
        # Add relevant metadata
        for key, value in memory.metadata.items():
            if isinstance(value, (str, int, float, bool)):
                prompt += f"- {key}: {value}\n"
        
        # Add related entities and relationships
        if memory.related_entities:
            prompt += f"\nRelated Entities: {len(memory.related_entities)} items"
        
        if memory.relationships:
            prompt += f"\nRelationships: {len(memory.relationships)} connections"
        
        # Add context information
        if context:
            prompt += f"\nContext Information:"
            for key, value in context.items():
                if key != 'related_memories':  # Skip to avoid prompt bloat
                    prompt += f"- {key}: {value}\n"
        
        # Add prior analyses for synthesizer/curator roles
        if self.role in [DebateRole.SYNTHESIZER, DebateRole.CURATOR] and prior_analyses:
            prompt += f"\nPrior Agent Analyses:\n"
            for analysis in prior_analyses:
                prompt += f"- {analysis.agent_role.value.title()}: Score {analysis.score:.2f}, Confidence {analysis.confidence:.2f}\n"
                prompt += f"  Reasoning: {analysis.reasoning[:200]}...\n"
        
        return prompt
    
    def _parse_analysis_response(self, response_text: str) -> Dict[str, float]:
        """Parse analysis response to extract numeric scores."""
        scores = {}
        
        # Try to parse JSON response
        try:
            import json
            if response_text.strip().startswith('{'):
                parsed = json.loads(response_text)
                for key, value in parsed.items():
                    if isinstance(value, (int, float)) and 0 <= value <= 1:
                        scores[key] = float(value)
        except (json.JSONDecodeError, ValueError):
            pass
        
        # Fallback: pattern matching for scores
        import re
        score_patterns = {
            'factual_score': r'faccual[^\\d]*(\\d\\.?\\d*)',
            'logical_score': r'logical[^\\d]*(\\d\\.?\\d*)',
            'evidence_score': r'evidence[^\\d]*(\\d\\.?\\d*)',
            'bias_score': r'bias[^\\d]*(\\d\\.?\\d*)',
            'overall_score': r'overall[^\\d]*(\\d\\.?\\d*)',
            'consensus_score': r'consensus[^\\d]*(\\d\\.?\\d*)',
            'trustworthiness_score': r'trustworthiness[^\\d]*(\\d\\.?\\d*)',
            'final_score': r'final[^\\d]*(\\d\\.?\\d*)'
        }
        
        for score_name, pattern in score_patterns.items():
            if score_name not in scores:
                match = re.search(pattern, response_text.lower())
                if match:
                    try:
                        score_val = float(match.group(1))
                        if 0 <= score_val <= 1:
                            scores[score_name] = score_val
                    except (ValueError, IndexError):
                        continue
        
        # Ensure we have at least an overall_score
        if 'overall_score' not in scores:
            # Use first available score or default to 0.5
            available_scores = [s for s in scores.values() if 0 <= s <= 1]
            scores['overall_score'] = available_scores[0] if available_scores else 0.5
        
        return scores
    
    def _calculate_confidence(self, response_text: str, scores: Dict[str, float]) -> float:
        """Calculate confidence in the analysis based on various factors."""
        confidence_factors = {}
        
        # Factor 1: Response completeness
        expected_keys = {
            DebateRole.ANALYZER: ['factual_score', 'logical_score', 'overall_score'],
            DebateRole.SYNTHESIZER: ['consensus_score', 'synthesis_quality', 'overall_score'], 
            DebateRole.CURATOR: ['trustworthiness_score', 'final_recommendation', 'overall_score']
        }
        
        expected = expected_keys.get(self.role, ['overall_score'])
        completeness = len([k for k in expected if k in scores]) / len(expected)
        confidence_factors['completeness'] = completeness
        
        # Factor 2: Score reasonableness
        overall_score = scores.get('overall_score', 0.5)
        score_reasonableness = 1.0 - abs(0.6 - overall_score)  # Peak confidence around 0.6
        confidence_factors['score_reasonableness'] = score_reasonableness
        
        # Factor 3: Response length (longer responses often more thoughtful)
        response_length_factor = min(1.0, len(response_text) / 500)  # Normalize to 0-1
        confidence_factors['response_length'] = response_length_factor
        
        # Factor 4: Numerical score presence
        explicit_scores = sum(1 for v in scores.values() if 0 <= v <= 1)
        score_presence = min(1.0, explicit_scores / 3)  # Expect at least 3 scores
        confidence_factors['score_presence'] = score_presence
        
        # Calculate weighted average confidence
        weights = {
            'completeness': 0.4,
            'score_reasonableness': 0.2, 
            'response_length': 0.2,
            'score_presence': 0.2
        }
        
        confidence = sum(
            confidence_factors[factor] * weight
            for factor, weight in weights.items()
            if factor in confidence_factors
        )
        
        return max(0.0, min(1.0, confidence))


class DebateSession:
    """Coordinates a debate session between multiple agents."""
    
    def __init__(self, client: GeminiClient, max_participants: int = 3):
        self.client = client
        self.max_participants = max_participants
        self.debate_id = f"debate_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        self.start_time = datetime.now(timezone.utc)
        self.status = DebateStatus.INITIALIZING
        
        # Agent configuration
        self.agent_configs = [
            (DebateRole.ANALYZER, ModelTier.SMART),      # Use smart tier for accuracy
            (DebateRole.SYNTHESIZER, ModelTier.MEDIUM),   # Medium tier for balance
            (DebateRole.CURATOR, ModelTier.SMART)          # Smart tier for final decision
        ]
        
        self.agents: List[DebateAgent] = []
        self.analyses: List[AgentAnalysis] = []
        
    async def initialize_debate(self, memory: Memory) -> None:
        """Initialize debate session and create agents."""
        try:
            # Create debate agents
            for role, tier in self.agent_configs:
                agent = DebateAgent(role, self.client, tier)
                self.agents.append(agent)
            
            self.status = DebateStatus.IN_PROGRESS
            logger.info(f"Debate session {self.debate_id} initialized with {len(self.agents)} agents")
            
        except Exception as e:
            self.status = DebateStatus.FAILED
            logger.error(f"Failed to initialize debate {self.debate_id}: {e}")
            raise
    
    async def run_debate(self, memory: Memory, context: Optional[Dict[str, Any]] = None) -> DebateResult:
        """Run complete debate session."""
        context = context or {}
        
        try:
            # Initialize debate
            await self.initialize_debate(memory)
            
            # Phase 1: Individual agent analyses
            self.analyses = []
            for agent in self.agents:
                # Pass previous analyses for synthesizer/curator roles
                prior_analyses = self.analyses if agent.role in [DebateRole.SYNTHESIZER, DebateRole.CURATOR] else []
                
                analysis = await agent.analyze_memory(memory, context, prior_analyses)
                self.analyses.append(analysis)
            
            # Phase 2: Calculate results
            result = self._calculate_debate_result(memory)
            
            self.status = DebateStatus.CONSENSUS_REACHED if result.confidence_level >= 0.6 else DebateStatus.NO_CONSENSUS
            
            logger.info(f"Debate {self.debate_id} completed: Score={result.final_score:.3f}, Confidence={result.confidence_level:.3f}")
            
            return result
            
        except Exception as e:
            self.status = DebateStatus.FAILED
            logger.error(f"Debate session {self.debate_id} failed: {e}")
            
            # Return failed result
            return DebateResult(
                debate_id=self.debate_id,
                memory_id=memory.id,
                final_score=0.0,
                confidence_level=0.0,
                decision="FAILED",
                participating_agents=[agent.agent_id for agent in self.agents],
                agent_analyses=self.analyses,
                consensus_score=0.0,
                duration_ms=0.0,
                recommendations=["Debate failed due to error"],
                timestamp=datetime.now(timezone.utc)
            )
    
    def _calculate_debate_result(self, memory: Memory) -> DebateResult:
        """Calculate final debate result from individual analyses."""
        end_time = datetime.now(timezone.utc)
        duration_ms = (end_time - self.start_time).total_seconds() * 1000
        
        if not self.analyses:
            return self._create_empty_result(memory, end_time, duration_ms)
        
        # Calculate weighted consensus score (higher weight for analyzer/curator)
        role_weights = {
            DebateRole.ANALYZER: 0.4,
            DebateRole.SYNTHESIZER: 0.2, 
            DebateRole.CURATOR: 0.4
        }
        
        weighted_scores = []
        total_weight = 0.0
        
        for analysis in self.analyses:
            weight = role_weights.get(analysis.agent_role, 1.0)
            weighted_score = analysis.score * weight
            weighted_scores.append(weighted_score)
            total_weight += weight
        
        consensus_score = sum(weighted_scores) / total_weight if total_weight > 0 else 0.0
        
        # Calculate final confidence (average of agent confidences, weighted by role importance)
        confidences = self._get_role_weighted_confidences(self.analyses)
        final_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        # Determine final decision
        final_decision = self._determine_decision(consensus_score, final_confidence)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(self.analyses, consensus_score, final_confidence)
        
        return DebateResult(
            debate_id=self.debate_id,
            memory_id=memory.id,
            final_score=consensus_score,
            confidence_level=final_confidence,
            decision=final_decision,
            participating_agents=[agent.agent_id for agent in self.agents],
            agent_analyses=self.analyses,
            consensus_score=consensus_score,
            duration_ms=duration_ms,
            recommendations=recommendations,
            timestamp=end_time
        )
    
    def _create_empty_result(self, memory: Memory, timestamp: datetime, duration_ms: float) -> DebateResult:
        """Create empty result for failed debates."""
        return DebateResult(
            debate_id=self.debate_id,
            memory_id=memory.id,
            final_score=0.0,
            confidence_level=0.0,
            decision="FAILED",
            participating_agents=[agent.agent_id for agent in self.agents],
            agent_analyses=[],
            consensus_score=0.0,
            duration_ms=duration_ms,
            recommendations=["No successful analyses completed"],
            timestamp=timestamp
        )
    
    def _get_role_weighted_confidences(self, analyses: List[AgentAnalysis]) -> List[float]:
        """Get confidences weighted by agent role importance."""
        role_multipliers = {
            DebateRole.ANALYZER: 1.2,  # More weight on accuracy
            DebateRole.SYNTHESIZER: 1.0,
            DebateRole.CURATOR: 1.3   # Most weight on final decision
        }
        
        weighted_confidences = []
        for analysis in analyses:
            multiplier = role_multipliers.get(analysis.agent_role, 1.0)
            weighted_conf = analysis.confidence * multiplier
            weighted_confidences.append(min(1.0, weighted_conf))  # Cap at 1.0
        
        return weighted_confidences
    
    def _determine_decision(self, final_score: float, confidence: float) -> str:
        """Determine final decision based on scores."""
        # High confidence and score
        if final_score >= 0.8 and confidence >= 0.7:
            return "ACCEPTED"
        
        # Moderate scores
        elif final_score >= 0.6 and confidence >= 0.5:
            return "REFINE_REQUESTED"
        
        # Low scores
        elif final_score < 0.4 or confidence < 0.3:
            return "REJECTED"
        
        # Borderline cases
        else:
            return "MANUAL_REVIEW_REQUIRED"
    
    def _generate_recommendations(self, analyses: List[AgentAnalysis], 
                                final_score: float, confidence: float) -> List[str]:
        """Generate actionable recommendations based on analyses."""
        recommendations = []
        
        # General recommendations based on final assessment
        if final_score >= 0.8 and confidence >= 0.7:
            recommendations.append("Memory is high quality - suitable for long-term retention")
        elif final_score >= 0.6:
            recommendations.append("Memory has good quality but consider minor refinements")
        else:
            recommendations.append("Memory requires significant improvement before acceptance")
        
        # Specific recommendations from agent analyses
        for analysis in analyses:
            reasoning_lower = analysis.reasoning.lower()
            
            if analysis.agent_role == DebateRole.ANALYZER:
                if "accuracy" in reasoning_lower and analysis.score < 0.7:
                    recommendations.append("Improve factual accuracy through verification")
                if "evidence" in reasoning_lower and analysis.score < 0.6:
                    recommendations.append("Strengthen supporting evidence")
                if "bias" in reasoning_lower:
                    recommendations.append("Address potential bias in content")
            
            elif analysis.agent_role == DebateRole.SYNTHESIZER:
                if "conflict" in reasoning_lower and analysis.score < 0.5:
                    recommendations.append("Resolve conflicts between information sources")
                if "consensus" in reasoning_lower and analysis.confidence < 0.6:
                    recommendations.append("Improve information consistency")
            
            elif analysis.agent_role == DebateRole.CURATOR:
                if "risk" in reasoning_lower and analysis.score < 0.6:
                    recommendations.append("Mitigate identified risks")
                if "trustworthiness" in reasoning_lower and analysis.score < 0.7:
                    recommendations.append("Enhance credibility and trustworthiness")
        
        return recommendations[:5]  # Limit to top 5 recommendations
    
    def get_session_metrics(self) -> Dict[str, Any]:
        """Get detailed session performance metrics."""
        if not self.analyses:
            return {"status": "no_analyses"}
        
        # Agent performance metrics
        agent_metrics = {}
        for analysis in self.analyses:
            role = analysis.agent_role.value
            if role not in agent_metrics:
                agent_metrics[role] = {
                    "scores": [],
                    "confidences": [],
                    "response_times": []
                }
            
            agent_metrics[role]["scores"].append(analysis.score)
            agent_metrics[role]["confidences"].append(analysis.confidence)
            
            rt = analysis.metadata.get("response_time_ms", 0)
            agent_metrics[role]["response_times"].append(rt)
        
        # Calculate averages per role
        for role in agent_metrics:
            metrics = agent_metrics[role]
            metrics["avg_score"] = sum(metrics["scores"]) / len(metrics["scores"])
            metrics["avg_confidence"] = sum(metrics["confidences"]) / len(metrics["confidences"])
            metrics["avg_response_time_ms"] = sum(metrics["response_times"]) / len(metrics["response_times"])
        
        return {
            "debate_id": self.debate_id,
            "status": self.status.value,
            "total_analyses": len(self.analyses),
            "agent_metrics": agent_metrics,
            "duration_ms": (datetime.now(timezone.utc) - self.start_time).total_seconds() * 1000
        }


# Factory functions for easy initialization
def create_debate_session(gemini_client: GeminiClient, max_participants: int = 3) -> DebateSession:
    """Create a configured debate session."""
    return DebateSession(gemini_client, max_participants)


def create_verification_debate(memory: Memory, gemini_api_key: Optional[str] = None) -> DebateSession:
    """Create debate session specifically for memory verification."""
    client = GeminiClient(api_key=gemini_api_key) if gemini_api_key else GeminiClient()
    return create_debate_session(client)
