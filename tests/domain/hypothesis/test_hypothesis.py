"""Tests for hypothesis domain."""

import pytest
from typing import List, Optional
from khala.domain.hypothesis.entities import Hypothesis
from khala.domain.hypothesis.value_objects import Evidence, EvidenceType, HypothesisStatus
from khala.domain.hypothesis.services import HypothesisService
from khala.domain.hypothesis.repositories import HypothesisRepository

class InMemoryHypothesisRepository(HypothesisRepository):
    """In-memory repository for testing."""
    
    def __init__(self):
        self.store = {}
        
    def save(self, hypothesis: Hypothesis) -> None:
        self.store[hypothesis.id] = hypothesis
        
    def find_by_id(self, hypothesis_id: str) -> Optional[Hypothesis]:
        return self.store.get(hypothesis_id)
        
    def find_all(self) -> List[Hypothesis]:
        return list(self.store.values())

def test_hypothesis_creation():
    repo = InMemoryHypothesisRepository()
    service = HypothesisService(repo)
    
    hypothesis = service.create_hypothesis(
        statement="The sky is blue.",
        reasoning="Visual observation."
    )
    
    assert hypothesis.statement == "The sky is blue."
    assert hypothesis.status == HypothesisStatus.PROPOSED
    assert hypothesis.confidence == 0.5

def test_adding_supporting_evidence():
    repo = InMemoryHypothesisRepository()
    service = HypothesisService(repo)
    hypothesis = service.create_hypothesis("Test", "Reason")
    
    evidence = Evidence(
        content="I saw it.",
        evidence_type=EvidenceType.OBSERVATION,
        confidence_score=0.9
    )
    
    service.add_evidence(hypothesis.id, evidence, supports=True)
    
    updated = service.get_hypothesis(hypothesis.id)
    assert len(updated.supporting_evidence) == 1
    assert updated.confidence > 0.5
    # With 0.9 support and 0.5 prior (weight 1), (0.9 + 0.5) / (0.9 + 1) = 1.4 / 1.9 = ~0.73
    assert updated.status == HypothesisStatus.TESTING

def test_validation_threshold():
    repo = InMemoryHypothesisRepository()
    service = HypothesisService(repo)
    hypothesis = service.create_hypothesis("Test", "Reason")
    
    # Add strong evidence
    e1 = Evidence("Strong proof", EvidenceType.EXPERIMENT, 1.0)
    e2 = Evidence("More proof", EvidenceType.EXPERIMENT, 1.0)
    
    service.add_evidence(hypothesis.id, e1, supports=True)
    service.add_evidence(hypothesis.id, e2, supports=True)
    
    updated = service.get_hypothesis(hypothesis.id)
    # (1+1 + 0.5) / (2 + 1) = 2.5 / 3 = 0.833 > 0.8
    assert updated.status == HypothesisStatus.VALIDATED

def test_rejection_threshold():
    repo = InMemoryHypothesisRepository()
    service = HypothesisService(repo)
    hypothesis = service.create_hypothesis("Test", "Reason")
    
    # Add strong contradicting evidence
    e1 = Evidence("Disproof", EvidenceType.EXPERIMENT, 1.0)
    e2 = Evidence("More disproof", EvidenceType.EXPERIMENT, 1.0)
    
    service.add_evidence(hypothesis.id, e1, supports=False)
    service.add_evidence(hypothesis.id, e2, supports=False)
    
    updated = service.get_hypothesis(hypothesis.id)
    # Support score = 0. Contradict score = 2.
    # (0 + 0.5) / (2 + 1) = 0.5 / 3 = 0.166 < 0.2
    assert updated.status == HypothesisStatus.REJECTED
