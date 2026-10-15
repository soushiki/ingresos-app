"""Motor de OCR con Gemini (Google). Transcribe; NO interpreta ni clasifica."""
from __future__ import annotations
import os, random, time
from .base import OCREngine
from .prompts import PROMPT, SYSTEM, clean_text

def _retryable(e: Exception) -> bool:
    code = getattr(e, "code", None) or getattr(e, "status_code", None)
    if code in (408, 429, 500, 502, 503, 504):
        return True
    s = str(e).upper()
    return any(k in s for k in ("429", "503", "UNAVAILABLE", "RESOURCE_EXHAUSTED", "TIMEOUT", "DEADLINE", "OVERLOADED"))


class GeminiEngine(OCREngine):
    name = "gemini"

    def __init__(self, api_key: str | None = None, model: str | None = None, retries: int = 4):
        from google import genai
        from google.genai import types
        key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not key:
            raise RuntimeError("Falta GEMINI_API_KEY (ponla en .env o como variable de entorno).")
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.retries = retries
        self._types = types
        self._client = genai.Client(api_key=key)

    def read(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> str:
        t = self._types
        cfg = t.GenerateContentConfig(system_instruction=SYSTEM, temperature=0.0, max_output_tokens=8192)
        part = t.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        last: Exception | None = None
        for i in range(self.retries + 1):
            try:
                r = self._client.models.generate_content(model=self.model, contents=[part, PROMPT], config=cfg)
                text = clean_text(r.text or "")
                if not text:
                    raise RuntimeError("Respuesta vacía (posible bloqueo de seguridad o imagen ilegible).")
                return text
            except Exception as e:  # noqa: BLE001
                last = e
                if i == self.retries or not _retryable(e):
                    break
                time.sleep(min(30.0, 2 ** i + random.random()))
        raise last  # type: ignore[misc]
