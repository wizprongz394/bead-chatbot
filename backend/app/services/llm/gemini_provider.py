"""Google Gemini provider via the google-generativeai SDK."""
import os


class GeminiProvider:
    def __init__(self, api_key=None, model=None, timeout=60.0):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "").strip()
        self.model_name = model or os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
        self.timeout = timeout
        self._model = None

    def _get_model(self):
        if self._model is None:
            if not self.api_key:
                raise RuntimeError("GEMINI_API_KEY not set")
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._model = genai.GenerativeModel(self.model_name)
        return self._model

    def is_available(self):
        return bool(self.api_key)

    def complete(self, system, user, temperature=0.3, max_tokens=500):
        if not self.is_available():
            raise RuntimeError("Gemini not configured")
        model = self._get_model()
        # Gemini doesn't have a separate system role in older versions;
        # we prepend it to the user message.
        combined = system.strip() + "\n\n" + user.strip()
        response = model.generate_content(
            combined,
            generation_config={
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            },
        )
        if hasattr(response, "text") and response.text:
            return response.text.strip()
        # Fallback for structured responses
        try:
            return response.candidates[0].content.parts[0].text.strip()
        except (AttributeError, IndexError):
            return ""
