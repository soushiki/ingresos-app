"""Normaliza cualquier imagen para que el motor de OCR la lea bien."""
from __future__ import annotations
import io
from pathlib import Path
from PIL import Image, ImageFilter, ImageOps

try:  # fotos de iPhone (.heic) si está instalado pillow-heif
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass

SUPPORTED = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".gif", ".heic", ".heif"}


def _cargar(source, enhance: bool = True) -> Image.Image:
    img = Image.open(io.BytesIO(source) if isinstance(source, (bytes, bytearray)) else source)
    img = ImageOps.exif_transpose(img)            # fotos de celular giradas
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        bg = Image.new("RGB", img.size, "white")
        bg.paste(img, mask=img.split()[-1])
        img = bg
    else:
        img = img.convert("RGB")
    return ImageOps.autocontrast(img, cutoff=1) if enhance else img   # papel gris / poca luz


def _jpeg(img: Image.Image, quality: int = 92) -> tuple[bytes, str]:
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=quality, optimize=True)
    return buf.getvalue(), "image/jpeg"


def prepare(source, max_side: int = 2600, min_side: int = 1200,
            quality: int = 92, enhance: bool = True) -> tuple[bytes, str]:
    """Devuelve (bytes JPEG, mime). Corrige rotación EXIF, transparencias, contraste y tamaño."""
    img = _cargar(source, enhance)
    w, h = img.size
    m = max(w, h)
    if m > max_side:                                # evita subir fotos de 20 MB
        s = max_side / m
        img = img.resize((round(w * s), round(h * s)), Image.LANCZOS)
    elif m < min_side:                              # capturas pequeñas
        s = min_side / m
        img = img.resize((round(w * s), round(h * s)), Image.LANCZOS)
    return _jpeg(img, quality)


def prepare_tiles(source, ancho: int = 1000, alto: int = 1500, solape: float = 0.15,
                  quality: int = 92, enhance: bool = True, **_) -> list[tuple[bytes, str]]:
    """Recibos largos y angostos (p. ej. 265×1540 px): se amplían y se parten en franjas con solape,
    porque un modelo de visión lee mal una imagen muy larga reducida de golpe. Si no es larga → 1 sola imagen."""
    img = _cargar(source, enhance)
    w, h = img.size
    if h / max(w, 1) < 2.2:
        return [prepare(source, quality=quality, enhance=enhance, **{k: v for k, v in _.items() if k in ("max_side", "min_side")})]
    s = min(max(ancho / w, 1.0), 4.0) if w < ancho else ancho / w
    img = img.resize((round(w * s), round(h * s)), Image.LANCZOS)
    if s > 1.2: img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=120, threshold=3))
    W, H = img.size
    paso = max(1, round(alto * (1 - solape)))
    out, y = [], 0
    while True:
        y1 = min(y + alto, H)
        out.append(_jpeg(img.crop((0, y, W, y1)), quality))
        if y1 >= H: break
        y += paso
    return out
