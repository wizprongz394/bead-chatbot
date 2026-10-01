"""Choose a provider based on environment."""
import os
from app.services.llm.ollama_provider import OllamaProvider
from app.services.llm.mock_provider import MockProvider

_PROVIDER = None


def get_provider():
    global _PROVIDER
    if _PROVIDER is not None:
        return _PROVIDER

    provider_name = os.environ.get("BEAD_LLM_PROVIDER", "auto").lower()

    if provider_name == "mock":
        _PROVIDER = MockProvider()
        return _PROVIDER

    if provider_name in ("auto", "ollama"):
        ollama = OllamaProvider(
            model=os.environ.get("BEAD_OLLAMA_MODEL", "qwen2.5-coder:7b"),
        )
        if ollama.is_available():
            _PROVIDER = ollama
            return _PROVIDER
        if provider_name == "ollama":
            raise RuntimeError("Ollama requested but not reachable at localhost:11434")

    _PROVIDER = MockProvider()
    return _PROVIDER
