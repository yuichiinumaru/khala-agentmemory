"""Natural triggers for memory operations."""

from enum import Enum
from typing import List, Tuple, Optional

class MemoryAction(Enum):
    """Actions triggered by natural language."""
    SAVE = "save"
    RETRIEVE = "retrieve"
    IGNORE = "ignore"
    UPDATE = "update"
    FORGET = "forget"

class TriggerHeuristics:
    """Heuristics for detecting memory triggers."""
    
    SAVE_PATTERNS = [
        "remember", "save this", "note that", "don't forget", 
        "keep in mind", "store this", "memorize"
    ]
    
    RETRIEVE_PATTERNS = [
        "what is", "who is", "recall", "remind me", 
        "do you know", "have we discussed", "search for"
    ]
    
    FORGET_PATTERNS = [
        "forget this", "delete this", "remove this", "ignore this"
    ]
    
    @classmethod
    def detect_action(cls, text: str) -> MemoryAction:
        """Detect the memory action implied by the text."""
        text_lower = text.lower()
        
        # Check explicit patterns
        if any(p in text_lower for p in cls.SAVE_PATTERNS):
            return MemoryAction.SAVE
            
        if any(p in text_lower for p in cls.FORGET_PATTERNS):
            return MemoryAction.FORGET
            
        if any(p in text_lower for p in cls.RETRIEVE_PATTERNS):
            return MemoryAction.RETRIEVE
            
        # Implicit heuristics
        # If it's a statement about the user or a fact, maybe save?
        if "i am" in text_lower or "my name" in text_lower or "i like" in text_lower:
            return MemoryAction.SAVE
            
        # If it's a question, retrieve
        if "?" in text:
            return MemoryAction.RETRIEVE
            
        return MemoryAction.IGNORE
