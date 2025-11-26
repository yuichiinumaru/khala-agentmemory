"""
Verification package for KHALA memory system.

Implements the 6-check verification gate and multi-agent debate system
for memory quality assurance.
"""

from .self_verification import SelfVerificationLoop
from .debate_system import DebateAgent, DebateSession, DebateResult
from .verification_gate import VerificationGate, VerificationCheck, VerificationResult

__all__ = [
    "SelfVerificationLoop",
    "DebateAgent", 
    "DebateSession",
    "DebateResult",
    "VerificationGate",
    "VerificationCheck", 
    "VerificationResult"
]
