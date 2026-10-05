"""Choose an LLM provider based on environment configuration.

Priority (when BEAD_LLM_PROVIDER=auto):
    1. OpenRouter (if OPENROUTER_API_KEY is set)
    2. Gemini     (if GEMINI_API_KEY is set)
    3. Ollama     (if reachable at localhost:11434)
    4. Mock       (always works — deterministic fallback)
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env", override=True)
from pathlib import Path
from dotenv import load_dotenv

# Load .env relative to backend/ so the factory works even if config.py
# hasn't been imported yet.
_ENV_PATH = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(_ENV_PATH, override=True)
_PROVIDER = None
_PROVIDER_NAME = None


def _build(provider_name):
    if provider_name == "openrouter":
        from app.services.llm.openrouter_provider import OpenRouterProvider
        return OpenRouterProvider()
    if provider_name == "gemini":
        from app.services.llm.gemini_provider import GeminiProvider
        return GeminiProvider()
    if provider_name == "ollama":
        from app.services.llm.ollama_provider import OllamaProvider
        return OllamaProvider(
            model=os.environ.get("BEAD_OLLAMA_MODEL", "qwen2.5-coder:7b")
        )
    from app.services.llm.mock_provider import MockProvider
    return MockProvider()


def get_provider():
    """Return the active provider, choosing based on env at first call."""
    global _PROVIDER, _PROVIDER_NAME
    if _PROVIDER is not None:
        return _PROVIDER

    requested = os.environ.get("BEAD_LLM_PROVIDER", "auto").lower().strip()

    # Explicit override
    if requested in ("openrouter", "gemini", "ollama", "mock"):
        provider = _build(requested)
        if requested != "mock" and hasattr(provider, "is_available") and not provider.is_available():
            raise RuntimeError(
                "BEAD_LLM_PROVIDER=" + requested + " was requested but the provider is not configured"
            )
        _PROVIDER = provider
        _PROVIDER_NAME = requested
        return _PROVIDER

    # Auto mode — try in priority order
    try:
        from app.services.llm.openrouter_provider import OpenRouterProvider
        orp = OpenRouterProvider()
        if orp.is_available():
            _PROVIDER = orp
            _PROVIDER_NAME = "openrouter"
            return _PROVIDER
    except Exception:
        pass

    try:
        from app.services.llm.gemini_provider import GeminiProvider
        gmp = GeminiProvider()
        if gmp.is_available():
            _PROVIDER = gmp
            _PROVIDER_NAME = "gemini"
            return _PROVIDER
    except Exception:
        pass

    try:
        from app.services.llm.ollama_provider import OllamaProvider
        olm = OllamaProvider()
        if olm.is_available():
            _PROVIDER = olm
            _PROVIDER_NAME = "ollama"
            return _PROVIDER
    except Exception:
        pass

    from app.services.llm.mock_provider import MockProvider
    _PROVIDER = MockProvider()
    _PROVIDER_NAME = "mock"
    return _PROVIDER


def provider_name():
    """Return the name of the active provider (useful for diagnostics)."""
    if _PROVIDER_NAME is None:
        get_provider()
    return _PROVIDER_NAME


def reset():
    """Force re-evaluation on next get_provider() call. Used by tests."""
    global _PROVIDER, _PROVIDER_NAME
    _PROVIDER = None
    _PROVIDER_NAME = None

