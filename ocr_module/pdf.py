"""PDF → texto (si trae capa de texto digital) o imagen por página (para el OCR)."""
from __future__ import annotations
import re

MIN_CARACTERES = 40          # menos que esto en una página = escaneada (hay que leerla como imagen)


def _pm():
    try:
        import pymupdf as pm
    except ImportError:
        try:
            import fitz as pm          # nombre antiguo del mismo paquete
        except ImportError as e:
            raise RuntimeError("Para leer PDF instala PyMuPDF:  pip install pymupdf") from e
    return pm


def abrir(data: bytes):
    pm = _pm()
    try:
        doc = pm.open(stream=data, filetype="pdf")
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"No pude abrir el PDF: {e}") from e
    if doc.needs_pass:
        raise RuntimeError("El PDF tiene contraseña")
    return doc


def _texto(page) -> str:
    return (page.get_text("text", sort=True) or "").strip()


def info(data: bytes) -> dict:
    """{'paginas': n, 'con_texto': [True, False, …]}: qué páginas ya traen texto digital."""
    doc = abrir(data)
    flags = [len(re.sub(r"\s", "", _texto(p))) >= MIN_CARACTERES for p in doc]
    return {"paginas": len(flags), "con_texto": flags}


def pagina(data: bytes, n: int, como_imagen: bool = False, dpi: int = 200) -> tuple:
    """Devuelve (texto, None) si la página tiene texto digital, o (None, bytes PNG) para leerla con el OCR."""
    doc = abrir(data)
    if not 1 <= n <= len(doc):
        raise RuntimeError(f"El PDF tiene {len(doc)} páginas; pediste la {n}")
    p = doc[n - 1]
    t = _texto(p)
    if not como_imagen and len(re.sub(r"\s", "", t)) >= MIN_CARACTERES:
        return t, None
    return None, p.get_pixmap(dpi=dpi).tobytes("png")
