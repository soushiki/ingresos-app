"""C2 · segundo lector (R3): Tesseract con lista blanca de dígitos y `.,$`. Devuelve el conjunto de números que ve.
Sin Tesseract devuelve None (y avisa una vez): R3 se salta, nunca inventa."""
from __future__ import annotations
import io, re, warnings

_LISTA = "0123456789.,$"
_avisado = False


def _enteros(texto: str) -> set:
    out = set()
    for tok in re.findall(r"\d[\d.,]*", texto):
        d = re.sub(r"\D", "", tok)
        if d: out.add(int(d))
        m = re.fullmatch(r"(\d[\d.,]*)[.,]\d{2}", tok)          # «45.000,00» → también 45000
        if m: out.add(int(re.sub(r"\D", "", m.group(1))))
    return out


def numeros_tesseract(img) -> set | None:
    """img: bytes o PIL.Image. Conjunto de enteros vistos, o None si Tesseract no está disponible."""
    global _avisado
    try:
        import pytesseract
        from PIL import Image
        pytesseract.get_tesseract_version()
        im = Image.open(io.BytesIO(img)) if isinstance(img, (bytes, bytearray)) else img
        txt = pytesseract.image_to_string(im.convert("L"), lang="eng",
                                          config=f"--psm 6 -c tessedit_char_whitelist={_LISTA}")
    except Exception as e:  # noqa: BLE001
        if not _avisado:
            warnings.warn(f"Tesseract no disponible: se omite el cruce de dígitos R3 ({e.__class__.__name__})")
            _avisado = True
        return None
    return _enteros(txt)
