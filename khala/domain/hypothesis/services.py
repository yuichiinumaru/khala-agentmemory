"""Service for managing hypotheses."""

from typing import Optional, List
from .entities import Hypothesis
from .value_objects import Evidence, HypothesisStatus
from .repositories import HypothesisRepository

class HypothesisService:
    """Service for hypothesis management."""
    
    def __init__(self, repository: HypothesisRepository):
        self.repository = repository
        
    def create_hypothesis(self, statement: str, reasoning: str) -> Hypothesis:
        """Create a new hypothesis."""
        hypothesis = Hypothesis(statement=statement, reasoning=reasoning)
        self.repository.save(hypothesis)
        return hypothesis
        
    def add_evidence(self, hypothesis_id: str, evidence: Evidence, supports: bool) -> Optional[Hypothesis]:
        """Add evidence to a hypothesis."""
        hypothesis = self.repository.find_by_id(hypothesis_id)
        if not hypothesis:
            return None
            
        hypothesis.add_evidence(evidence, supports)
        self.repository.save(hypothesis)
        return hypothesis
        
    def get_hypothesis(self, hypothesis_id: str) -> Optional[Hypothesis]:
        """Get a hypothesis by ID."""
        return self.repository.find_by_id(hypothesis_id)

    def conclude_hypothesis(self, hypothesis_id: str) -> Optional[Hypothesis]:
        """Force a conclusion based on current confidence."""
        hypothesis = self.repository.find_by_id(hypothesis_id)
        if not hypothesis:
            return None
            
        # If inconclusive but we need a decision, we might set it to INCONCLUSIVE explicitly
        # or leave it as is. For now, let's just ensure the status reflects the confidence.
        hypothesis.evaluate()
        
        if hypothesis.status == HypothesisStatus.TESTING:
            # If still testing but forced to conclude, mark as inconclusive
            hypothesis.status = HypothesisStatus.INCONCLUSIVE
            
        self.repository.save(hypothesis)
        return hypothesis
