"""Módulo 1 · Imagen → texto plano digitalizado.

    from ocr_module import digitize, digitize_many
    r = digitize("planilla.jpg");  print(r.text)
"""
from __future__ import annotations
import difflib, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from .base import OCREngine, OCRResult
from .preprocess import SUPPORTED, prepare, prepare_tiles

__all__ = ["digitize", "digitize_many", "collect_images", "get_engine", "OCRResult", "OCREngine"]


def _n(s: str) -> str:
    return " ".join(s.lower().split())


def unir(textos: list[str]) -> str:
    """Une la lectura de varias franjas quitando las líneas repetidas por el solape (solo en la costura)."""
    out = [l for l in textos[0].splitlines()] if textos else []
    for t in textos[1:]:
        nuevo = t.splitlines()
        for k in range(min(8, len(out), len(nuevo)), 0, -1):
            if all(_n(a) == _n(b) or difflib.SequenceMatcher(None, _n(a), _n(b)).ratio() >= 0.92
                   for a, b in zip(out[-k:], nuevo[:k])):
                nuevo = nuevo[k:]; break
        out += nuevo
    return "\n".join(out)


def get_engine(name: str = "local", **kw) -> OCREngine:
    """'local' (Ollama/LM Studio, gratis) · 'tesseract' (sin IA, solo impreso) · 'gemini' (API de Google)."""
    if name in ("local", "ollama"):
        from .local_engine import LocalVLMEngine
        return LocalVLMEngine(**kw)
    if name == "tesseract":
        from .tesseract_engine import TesseractEngine
        return TesseractEngine(**kw)
    if name == "gemini":
        from .gemini_engine import GeminiEngine
        return GeminiEngine(**kw)
    raise ValueError(f"Motor desconocido: {name}")


def digitize(source, engine: OCREngine | None = None, preprocess: bool = True) -> OCRResult:
    """Una imagen (ruta, Path o bytes) → OCRResult. Nunca lanza excepción: revisa .ok"""
    engine = engine or get_engine()
    label = source if isinstance(source, str) else (str(source) if isinstance(source, Path) else "bytes")
    t0 = time.time()
    try:
        if preprocess:
            partes = prepare_tiles(source, **getattr(engine, "prep", {}))
        else:
            partes = [(source if isinstance(source, (bytes, bytearray)) else Path(source).read_bytes(), "image/jpeg")]
        text = unir([engine.read(d, m) for d, m in partes])
        return OCRResult(label, text, True, "", engine.name, engine.model, round(time.time() - t0, 2))
    except Exception as e:  # noqa: BLE001
        return OCRResult(label, "", False, f"{type(e).__name__}: {e}", engine.name, engine.model,
                         round(time.time() - t0, 2))


def digitize_many(sources, engine: OCREngine | None = None, workers: int = 4,
                  preprocess: bool = True, on_progress=None) -> list[OCRResult]:
    """Muchas imágenes en paralelo. Conserva el orden de entrada."""
    engine = engine or get_engine()
    sources = list(sources)
    done = 0
    def job(s):
        nonlocal done
        r = digitize(s, engine, preprocess)
        done += 1
        if on_progress:
            on_progress(done, len(sources), r)
        return r
    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        return list(ex.map(job, sources))


def collect_images(*paths) -> list[Path]:
    """Acepta archivos y carpetas; devuelve las imágenes soportadas, ordenadas."""
    out: list[Path] = []
    for p in map(Path, paths):
        if p.is_dir():
            out += sorted(f for f in p.rglob("*") if f.suffix.lower() in SUPPORTED)
        elif p.suffix.lower() in SUPPORTED:
            out.append(p)
    return out
