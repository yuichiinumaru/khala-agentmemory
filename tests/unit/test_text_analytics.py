import unittest
from khala.application.services.text_analytics_service import TextAnalyticsService

class TestTextAnalyticsService(unittest.TestCase):
    def setUp(self):
        self.service = TextAnalyticsService()

    def test_calculate_complexity_easy(self):
        text = "The cat sat on the mat. It was a good cat."
        # Very easy text
        score = self.service.calculate_complexity(text)
        self.assertTrue(score > 80, f"Expected > 80, got {score}")

    def test_calculate_complexity_hard(self):
        text = "The physiological mechanisms underlying the phenomenon of photosynthesis are intricate and multifaceted, involving complex biochemical pathways."
        # Hard text (long words, long sentence)
        score = self.service.calculate_complexity(text)
        self.assertTrue(score < 50, f"Expected < 50, got {score}")

    def test_empty_text(self):
        self.assertEqual(self.service.calculate_complexity(""), 0.0)
        self.assertEqual(self.service.calculate_complexity(None), 0.0)

    def test_syllable_count(self):
        self.assertEqual(self.service._count_syllables("cat"), 1)
        self.assertEqual(self.service._count_syllables("hello"), 2)
        self.assertEqual(self.service._count_syllables("beautiful"), 3)

    def test_sentence_count(self):
        text = "Hello world. How are you? I am fine!"
        self.assertEqual(self.service._count_sentences(text), 3)

if __name__ == "__main__":
    unittest.main()
