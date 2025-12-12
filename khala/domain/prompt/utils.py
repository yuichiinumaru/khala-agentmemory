"""Prompt Utility module for Object-Oriented Prompting.

Ported and adapted from `prompt-string` to work with Khala's Gemini stack.
Removes `tiktoken` dependency in favor of a simple length proxy or future Gemini tokenizer integration.
"""

from typing import Optional, Literal, List, Dict, Any, Union
from functools import wraps

# Since we don't want to depend on tiktoken for Gemini, we will use a simplified
# length check or simple word count for now.
# In the future, we can inject Gemini's `count_tokens` API here.

def simple_token_count(text: str) -> int:
    """Approximate token count for Gemini (rough estimate 4 chars/token)."""
    # Ensure at least 1 token if there is text
    if not text:
        return 0
    return max(1, len(text) // 4)

def to_prompt_string(func):
    """Decorator to ensure methods return a PromptString instance."""
    @wraps(func)
    def wrapper(self: "PromptString", *args, **kwargs):
        result = func(self, *args, **kwargs)
        # If result is already PromptString, return it
        if isinstance(result, PromptString):
            return result
        # If result is string, wrap it
        if isinstance(result, str):
            return PromptString(result, **self._meta_info)
        return result
    return wrapper


class PromptString(str):
    """String subclass that carries role and metadata information."""

    def __new__(
        cls,
        content: str,
        role: Optional[Literal["system", "user", "assistant", "model"]] = None,
        **kwargs,
    ):
        instance = str.__new__(cls, content)
        instance.__prompt_string_role = role
        instance.__prompt_string_kwargs = {
            "role": role,
            **kwargs
        }
        return instance

    @property
    def role(self) -> Optional[str]:
        return self.__prompt_string_role

    @property
    def _meta_info(self) -> Dict[str, Any]:
        return self.__prompt_string_kwargs

    @role.setter
    def role(self, value: str):
        self.__prompt_string_role = value
        self.__prompt_string_kwargs["role"] = value

    @property
    def token_count(self) -> int:
        """Returns approximate token count."""
        return simple_token_count(str(self))

    @to_prompt_string
    def __getitem__(self, index):
        return super().__getitem__(index)

    def message(self, style="openai") -> Dict[str, str]:
        """Convert to message dict format."""
        # 'openai' style is standard {role, content} which fits Gemini (mostly)
        # Gemini uses 'user'/'model' often, but 'assistant' is mapped usually.
        return {
            "role": self.role or "user",
            "content": str(self),
        }

    def __add__(self, other: Union["PromptString", str]) -> "PromptString":
        if isinstance(other, PromptString):
            # Concatenate content, keep self metadata
            return PromptString(super().__add__(other), **self._meta_info)
        elif isinstance(other, str):
            return PromptString(super().__add__(other), **self._meta_info)
        else:
            raise ValueError(f"Invalid type for Prompt Concatenation: {type(other)}")

    def __truediv__(self, other: Union["PromptString", "PromptChain"]) -> "PromptChain":
        """Division operator `/` creates a PromptChain."""
        if isinstance(other, PromptString):
            return PromptChain([self, other])
        elif isinstance(other, PromptChain):
            return PromptChain([self] + other.prompts)
        else:
            raise ValueError(f"Invalid type for Prompt Division: {type(other)}")

    @to_prompt_string
    def replace(self, old: str, new: str, count: int = -1) -> "PromptString":
        return super().replace(old, new, count)

    @to_prompt_string
    def format(self, *args, **kwargs) -> "PromptString":
        return super().format(*args, **kwargs)


class PromptChain:
    """A sequence of PromptStrings."""

    def __init__(self, prompts: List[PromptString], default_start_role: str = "user"):
        self.__prompts = prompts
        self.__start_role = default_start_role

    def __len__(self):
        return len(self.__prompts)

    def __getitem__(self, index):
        if isinstance(index, int):
            return self.__prompts[index]
        elif isinstance(index, slice):
            return PromptChain(
                self.__prompts[index], default_start_role=self.__start_role
            )
        else:
            raise ValueError(f"Invalid index type: {type(index)}")

    @property
    def roles(self) -> List[Optional[str]]:
        return [p.role for p in self.__prompts]

    @property
    def prompts(self) -> List[PromptString]:
        return self.__prompts

    def __truediv__(self, other: Union["PromptString", "PromptChain"]) -> "PromptChain":
        if isinstance(other, PromptChain):
            return PromptChain(
                self.prompts + other.prompts, default_start_role=self.__start_role
            )
        elif isinstance(other, PromptString):
            return PromptChain(
                self.prompts + [other], default_start_role=self.__start_role
            )
        else:
            raise ValueError(f"Invalid type for PromptChain Division: {type(other)}")

    def messages(self, style="openai") -> List[Dict[str, str]]:
        """Returns list of message dicts."""
        return [p.message(style=style) for p in self.__prompts]

    def __str__(self):
        return str(self.messages())


# Helper Classes for cleaner API
class System(PromptString):
    def __new__(cls, content: str, **kwargs):
        return PromptString.__new__(cls, content, role="system", **kwargs)

class User(PromptString):
    def __new__(cls, content: str, **kwargs):
        return PromptString.__new__(cls, content, role="user", **kwargs)

class Assistant(PromptString):
    def __new__(cls, content: str, **kwargs):
        # Map 'assistant' to 'model' for Gemini if needed later, but keeping 'assistant' for generic use
        return PromptString.__new__(cls, content, role="assistant", **kwargs)

# For Gemini specific role naming
class Model(PromptString):
    def __new__(cls, content: str, **kwargs):
        return PromptString.__new__(cls, content, role="model", **kwargs)
