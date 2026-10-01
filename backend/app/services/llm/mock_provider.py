"""Mock provider. Deterministic, no network. Used as fallback when Ollama is down."""
class MockProvider:
    def is_available(self):
        return True

    def complete(self, system, user, temperature=0.3, max_tokens=500):
        # The mock provider doesn't actually generate prose.
        # It returns an empty string, and callers are expected to have
        # a deterministic fallback path when the LLM returns nothing.
        return ""
