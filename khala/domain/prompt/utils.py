from typing import List, Dict, Any, Union, Optional

class PromptString:
    def __init__(self, content: str, role: str = "user"):
        self.content = content
        self.role = role

    def format(self, **kwargs) -> 'PromptString':
        return self.__class__(self.content.format(**kwargs))

    def __str__(self) -> str:
        return self.content

    def __truediv__(self, other: Union['PromptString', str, None]) -> 'PromptChain':
        if other is None:
            return PromptChain([self])
        if isinstance(other, str):
            other = User(other)
        if isinstance(other, PromptChain):
            return PromptChain([self] + other.parts)
        if isinstance(other, PromptString):
            return PromptChain([self, other])
        return PromptChain([self]) # Fallback

    def messages(self) -> List[Dict[str, Any]]:
        # Gemini format: role, parts (list of text)
        return [{"role": self.role, "parts": [self.content]}]

    def __eq__(self, other):
        return isinstance(other, PromptString) and self.content == other.content and self.role == other.role

class System(PromptString):
    def __init__(self, content: str):
        super().__init__(content, role="system")

class User(PromptString):
    def __init__(self, content: str):
        super().__init__(content, role="user")

class Assistant(PromptString):
    def __init__(self, content: str):
        # Gemini uses 'model' for assistant responses in history
        super().__init__(content, role="model")

class PromptChain:
    def __init__(self, parts: List[PromptString]):
        self.parts = parts

    def __str__(self) -> str:
        return "\n\n".join(str(p) for p in self.parts)

    def messages(self) -> List[Dict[str, Any]]:
        msgs = []
        for p in self.parts:
            msgs.extend(p.messages())
        return msgs

    def __truediv__(self, other: Union[PromptString, str, None]) -> 'PromptChain':
        if other is None:
            return self
        if isinstance(other, str):
            other = User(other)
        if isinstance(other, PromptChain):
            return PromptChain(self.parts + other.parts)
        if isinstance(other, PromptString):
            return PromptChain(self.parts + [other])
        return self
