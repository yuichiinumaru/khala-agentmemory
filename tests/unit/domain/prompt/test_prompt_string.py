import unittest
from khala.domain.prompt.utils import PromptString, PromptChain, System, User, Assistant

class TestPromptString(unittest.TestCase):
    def test_initialization(self):
        ps = PromptString("Hello", role="user")
        self.assertEqual(str(ps), "Hello")
        self.assertEqual(ps.role, "user")

        # Test Truthiness (was broken before)
        ps_short = PromptString("Hi")
        self.assertTrue(ps_short)

        ps_empty = PromptString("")
        self.assertFalse(ps_empty)

    def test_token_count(self):
        ps = PromptString("Hello World")
        # simple_token_count = max(1, len // 4)
        # 11 chars // 4 = 2
        self.assertEqual(ps.token_count, 2)

        ps_tiny = PromptString("A")
        self.assertEqual(ps_tiny.token_count, 1)

    def test_helpers(self):
        sys = System("Act as a distinct agent.")
        user = User("What is your name?")
        ai = Assistant("I am Khala.")

        self.assertEqual(sys.role, "system")
        self.assertEqual(user.role, "user")
        self.assertEqual(ai.role, "assistant")

    def test_concatenation(self):
        p1 = PromptString("Hello", role="user")
        p2 = PromptString(" World")
        combined = p1 + p2
        self.assertEqual(str(combined), "Hello World")
        self.assertEqual(combined.role, "user") # Inherits first role

    def test_formatting(self):
        template = PromptString("Hello {name}", role="user")
        formatted = template.format(name="Khala")
        self.assertEqual(str(formatted), "Hello Khala")
        self.assertEqual(formatted.role, "user")

    def test_chaining(self):
        sys = System("Sys")
        user = User("User")

        # Division operator creates chain
        chain = sys / user
        self.assertIsInstance(chain, PromptChain)
        self.assertEqual(len(chain), 2)

        msgs = chain.messages()
        self.assertEqual(msgs[0]["role"], "system")
        self.assertEqual(msgs[0]["content"], "Sys")
        self.assertEqual(msgs[1]["role"], "user")
        self.assertEqual(msgs[1]["content"], "User")

    def test_prompt_string_replace(self):
        ps = PromptString("Hello World", role="user")
        replaced = ps.replace("World", "Khala")
        self.assertEqual(str(replaced), "Hello Khala")
        self.assertEqual(replaced.role, "user")
        self.assertIsInstance(replaced, PromptString)

if __name__ == "__main__":
    unittest.main()
