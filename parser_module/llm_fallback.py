"""OPCIONAL: pide al modelo local que complete SOLO los campos que las reglas no encontraron.
Seguridad: acepta únicamente cifras que ya estén escritas en el texto (la IA no puede inventar montos)
y todo lo que aporta queda marcado «revisar»."""
from __future__ import annotations
import json, os, re
import requests
from .parser import Cierre, montos_del_texto


def completar(cierre: Cierre, base_url: str | None = None, model: str | None = None, timeout: int = 300) -> Cierre:
    faltan = [k for k, c in cierre.campos.items() if c.estado == "faltante"]
    if not faltan or not cierre.texto.strip():
        return cierre
    base = (base_url or os.getenv("LOCAL_VLM_URL", "http://localhost:11434/v1")).rstrip("/")
    lista = "\n".join(f"- {k}: {cierre.nombres[k]} ({'conteo' if cierre.tipos[k] == 'conteo' else 'dinero'})" for k in faltan)
    prompt = (f"Este es el texto de un cierre de caja manuscrito (puede estar desordenado):\n\n{cierre.texto}\n\n"
              f"Busca SOLO estos campos que no pude encontrar:\n{lista}\n\n"
              "Devuelve únicamente un JSON {\"campo\": entero_o_null}. Usa null si el campo no está en el texto. "
              "Usa solo números que aparezcan escritos en el texto, sin símbolos ni separadores. No inventes nada.")
    try:
        r = requests.post(f"{base}/chat/completions", timeout=timeout,
                          headers={"Authorization": f"Bearer {os.getenv('LOCAL_VLM_KEY', 'ollama')}"},
                          json={"model": model or os.getenv("LOCAL_VLM_MODEL", "qwen2.5vl:7b"), "temperature": 0,
                                "messages": [{"role": "user", "content": prompt}]})
        r.raise_for_status()
        txt = re.sub(r"<think>.*?</think>", "", r.json()["choices"][0]["message"]["content"] or "", flags=re.S)
        data = json.loads(re.search(r"\{.*\}", txt, re.S).group(0))
    except Exception as e:  # noqa: BLE001
        cierre.advertencias.append(f"Apoyo con IA no disponible: {type(e).__name__}")
        return cierre
    validos = montos_del_texto(cierre.texto)
    for k in faltan:
        v = data.get(k)
        if isinstance(v, (int, float)) and not isinstance(v, bool) and int(v) in validos:
            c = cierre.campos[k]
            c.valor, c.estado, c.fuente, c.confianza = int(v), "revisar", "ia", 0.5
            c.razones = ["interpretado por IA: verificar contra la foto"]
    return cierre
