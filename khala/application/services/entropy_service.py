import math
from collections import Counter

class EntropyService:
    """Service for calculating information entropy of text."""

    def calculate_shannon_entropy(self, text: str) -> float:
        """Calculate Shannon entropy of a string."""
        if not text:
            return 0.0

        counts = Counter(text)
        length = len(text)

        entropy = 0.0
        for count in counts.values():
            probability = count / length
            entropy -= probability * math.log2(probability)

        return entropy

    def should_trigger_consolidation(self, text: str, threshold: float = 4.5) -> bool:
        """Determine if entropy suggests high information density requiring consolidation."""
        # This is a heuristic. Higher entropy = more random/dense?
        # Actually, consolidation reduces redundancy (lowers entropy?).
        # High entropy might mean 'lots of unique info'.
        # For now, we implement the metric storage.
        return self.calculate_shannon_entropy(text) > threshold
