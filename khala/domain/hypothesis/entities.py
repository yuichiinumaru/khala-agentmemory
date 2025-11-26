"""Hypothesis entity definition."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import uuid

from .value_objects import HypothesisStatus, Evidence

@dataclass
class Hypothesis:
    """Entity representing a scientific hypothesis."""
    
    statement: str
    reasoning: str
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: HypothesisStatus = HypothesisStatus.PROPOSED
    confidence: float = 0.5  # Initial neutral confidence
    
    supporting_evidence: List[Evidence] = field(default_factory=list)
    contradicting_evidence: List[Evidence] = field(default_factory=list)
    
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_evidence(self, evidence: Evidence, supports: bool) -> None:
        """Add evidence to the hypothesis and re-evaluate."""
        if supports:
            self.supporting_evidence.append(evidence)
        else:
            self.contradicting_evidence.append(evidence)
        
        self.updated_at = datetime.now(timezone.utc)
        self.evaluate()

    def evaluate(self) -> None:
        """Evaluate the hypothesis based on current evidence."""
        # Simple Bayesian-like update or weighted average could go here.
        # For now, we'll use a weighted score approach.
        
        support_score = sum(e.confidence_score for e in self.supporting_evidence)
        contradict_score = sum(e.confidence_score for e in self.contradicting_evidence)
        
        total_evidence = support_score + contradict_score
        
        if total_evidence == 0:
            self.confidence = 0.5
            self.status = HypothesisStatus.PROPOSED
            return

        # Calculate raw confidence towards truth
        # If support > contradict, confidence > 0.5
        # If contradict > support, confidence < 0.5
        
        # Normalize to 0-1 range where 1 is fully supported, 0 is fully contradicted
        # We add a small prior (0.5) with weight 1 to avoid extreme swings with little evidence
        prior = 0.5
        prior_weight = 1.0
        
        self.confidence = (support_score + (prior * prior_weight)) / (total_evidence + prior_weight)
        
        # Update status based on thresholds
        if self.confidence > 0.8:
            self.status = HypothesisStatus.VALIDATED
        elif self.confidence < 0.2:
            self.status = HypothesisStatus.REJECTED
        elif len(self.supporting_evidence) + len(self.contradicting_evidence) > 0:
            self.status = HypothesisStatus.TESTING
        else:
            self.status = HypothesisStatus.PROPOSED
