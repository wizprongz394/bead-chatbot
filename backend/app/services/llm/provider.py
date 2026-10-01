"""Abstract LLM provider. Swap implementations without touching callers."""
from typing import Protocol


class LLMProvider(Protocol):
    def complete(self, system: str, user: str, temperature: float = 0.3, max_tokens: int = 500) -> str:
        ...

    def is_available(self) -> bool:
        ...
