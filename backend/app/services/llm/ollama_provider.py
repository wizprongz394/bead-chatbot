"""Ollama provider. Uses the local Ollama HTTP API."""
import json
import httpx


class OllamaProvider:
    def __init__(self, base_url="http://localhost:11434", model="qwen2.5-coder:7b", timeout=60.0):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def is_available(self):
        try:
            with httpx.Client(timeout=3.0) as client:
                r = client.get(f"{self.base_url}/api/tags")
                return r.status_code == 200
        except Exception:
            return False

    def complete(self, system, user, temperature=0.3, max_tokens=500):
        payload = {
            "model": self.model,
            "prompt": user,
            "system": system,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                r = client.post(f"{self.base_url}/api/generate", json=payload)
                r.raise_for_status()
                data = r.json()
                return data.get("response", "").strip()
        except Exception as e:
            raise RuntimeError(f"Ollama call failed: {e}")
