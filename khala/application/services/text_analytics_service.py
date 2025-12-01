import re
from typing import List

class TextAnalyticsService:
    """Service for advanced text analytics."""

    def calculate_complexity(self, text: str) -> float:
        """
        Calculate the Flesch-Kincaid Reading Ease score.

        Formula: 206.835 - 1.015 * (total_words / total_sentences) - 84.6 * (total_syllables / total_words)

        Returns:
            Float score. Higher is easier.
            0-30: College graduate (Very Difficult)
            60-70: 13-15 years old (Standard)
            90-100: 11 years old (Very Easy)
        """
        if not text or not text.strip():
            return 0.0

        sentences = self._count_sentences(text)
        words = self._count_words(text)
        syllables = self._count_syllables_in_text(text)

        if sentences == 0 or words == 0:
            return 0.0

        score = 206.835 - 1.015 * (words / sentences) - 84.6 * (syllables / words)
        return round(score, 2)

    def _count_sentences(self, text: str) -> int:
        """Count sentences using punctuation."""
        return len(re.findall(r'[.!?]+', text)) or 1

    def _count_words(self, text: str) -> int:
        """Count words."""
        return len(re.findall(r'\b\w+\b', text))

    def _count_syllables_in_text(self, text: str) -> int:
        """Count total syllables."""
        words = re.findall(r'\b\w+\b', text)
        return sum(self._count_syllables(word) for word in words)

    def _count_syllables(self, word: str) -> int:
        """Heuristic syllable counting."""
        word = word.lower()
        if len(word) <= 3:
            return 1

        count = 0
        vowels = "aeiouy"
        if word[0] in vowels:
            count += 1
        for index in range(1, len(word)):
            if word[index] in vowels and word[index - 1] not in vowels:
                count += 1
        if word.endswith("e"):
            count -= 1
        if count == 0:
            count += 1
        return count
