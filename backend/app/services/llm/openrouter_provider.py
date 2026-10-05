"""OpenRouter provider. Uses the OpenAI-compatible chat completions API."""
import os
from openai import OpenAI


class OpenRouterProvider:
    def __init__(self, api_key=None, model=None, timeout=60.0):
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "").strip()
        self.model = model or os.environ.get(
            "OPENROUTER_MODEL", "google/gemini-2.0-flash-001"
        )
        self.timeout = timeout
        self._client = None

    def _get_client(self):
        if self._client is None:
            if not self.api_key:
                raise RuntimeError("OPENROUTER_API_KEY not set")
            self._client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=self.api_key,
                timeout=self.timeout,
            )
        return self._client

    def is_available(self):
        return bool(self.api_key)

    def complete(self, system, user, temperature=0.3, max_tokens=500):
        if not self.is_available():
            raise RuntimeError("OpenRouter not configured")
        client = self._get_client()
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if not response.choices:
            return ""
        return (response.choices[0].message.content or "").strip()
