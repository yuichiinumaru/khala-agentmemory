import pytest
from khala.domain.prompt.utils import PromptString, System, User, Assistant, PromptChain

def test_prompt_roles():
    s = System("System context")
    u = User("User query")
    a = Assistant("Model response")

    assert s.role == "system"
    assert u.role == "user"
    # Gemini uses 'model', OpenAI uses 'assistant'. We align with Agno/Gemini usually.
    # Agno uses 'model' or 'assistant'? Gemini API expects 'model' for chat history.
    # Let's standardize on 'model' for Assistant to match Gemini.
    assert a.role == "model"

def test_prompt_formatting():
    p = User("Hello {name}")
    f = p.format(name="World")
    assert str(f) == "Hello World"
    assert f.role == "user"
    assert isinstance(f, User)

def test_concatenation_operator():
    s = System("Be helpful.")
    u = User("Hi")

    chain = s / u

    assert isinstance(chain, PromptChain)
    assert len(chain.parts) == 2
    assert chain.parts[0] == s
    assert chain.parts[1] == u

    # String representation joins with double newline
    assert str(chain) == "Be helpful.\n\nHi"

def test_messages_export():
    chain = System("S") / User("U") / Assistant("A")
    msgs = chain.messages()

    assert len(msgs) == 3
    assert msgs[0] == {"role": "system", "parts": ["S"]} # Gemini format often uses 'parts' list
    assert msgs[1] == {"role": "user", "parts": ["U"]}
    assert msgs[2] == {"role": "model", "parts": ["A"]}

def test_chain_extension():
    c1 = System("S") / User("U")
    c2 = c1 / Assistant("A")

    assert len(c2.parts) == 3
    assert str(c2) == "S\n\nU\n\nA"

def test_rshift_pipeline():
    # If we implement pipe operator for something? Maybe not needed for Phase 2.
    pass
