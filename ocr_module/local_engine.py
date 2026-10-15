"""Motor LOCAL y gratuito: cualquier modelo de visión servido por Ollama, LM Studio, vLLM, etc.
Usa la API compatible con OpenAI, así que no hace falta ninguna suscripción ni clave."""
from __future__ import annotations
import base64, os, time
import requests
from .base import OCREngine
from .prompts import PROMPT, SYSTEM, clean_text


class LocalVLMEngine(OCREngine):
    name = "local"
    prep = {"max_side": 1800}          # imágenes más livianas: menos memoria y más rápido

    def __init__(self, base_url: str | None = None, model: str | None = None,
                 api_key: str | None = None, timeout: int = 300, retries: int = 2):
        self.base_url = (base_url or os.getenv("LOCAL_VLM_URL", "http://localhost:11434/v1")).rstrip("/")
        self.model = model or os.getenv("LOCAL_VLM_MODEL", "qwen2.5vl:7b")
        self.api_key = api_key or os.getenv("LOCAL_VLM_KEY", "ollama")
        self.timeout, self.retries = timeout, retries

    def read(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> str:
        b64 = base64.b64encode(image_bytes).decode()
        payload = {
            "model": self.model, "temperature": 0, "max_tokens": 4096,
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": [
                    {"type": "text", "text": PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64}"}},
                ]},
            ],
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        last: Exception | None = None
        for i in range(self.retries + 1):
            try:
                r = requests.post(f"{self.base_url}/chat/completions", json=payload,
                                  headers=headers, timeout=self.timeout)
                if r.status_code == 404 or "not found" in r.text.lower()[:300]:
                    raise RuntimeError(f"El modelo '{self.model}' no está instalado. Ejecuta: ollama pull {self.model}")
                if r.status_code >= 500:
                    raise requests.HTTPError(f"{r.status_code}: {r.text[:200]}")
                r.raise_for_status()
                text = clean_text(r.json()["choices"][0]["message"].get("content") or "")
                if not text:
                    raise RuntimeError("El modelo devolvió una respuesta vacía.")
                return text
            except requests.ConnectionError:
                raise RuntimeError(f"No puedo conectar con {self.base_url}. ¿Está corriendo Ollama (ollama serve)?")
            except (requests.Timeout, requests.HTTPError) as e:
                last = e
                if i < self.retries:
                    time.sleep(2 ** i)
        raise last  # type: ignore[misc]
