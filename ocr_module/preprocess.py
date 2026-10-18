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


def variantes(img: Image.Image) -> list[tuple[str, Image.Image]]:
    """C1: 4 versiones de la misma imagen para releer una foto dudosa.
    V0 = tal cual; V1 = ampliada 1,5x; V2 = gris + autocontraste; V3 = recorte con 3 % menos de margen por lado."""
    img = img.convert("RGB")
    w, h = img.size
    v1 = img.resize((round(w * 1.5), round(h * 1.5)), Image.LANCZOS)
    v2 = ImageOps.autocontrast(ImageOps.grayscale(img), cutoff=1).convert("RGB")
    dx, dy = round(w * 0.03), round(h * 0.03)
    v3 = img.crop((dx, dy, w - dx, h - dy))
    return [("V0", img), ("V1", v1), ("V2", v2), ("V3", v3)]


REALESRGAN = Path(__file__).resolve().parent.parent / "datos" / "herramientas" / "realesrgan" / "realesrgan-ncnn-vulkan.exe"


def _realesrgan_exe() -> str | None:
    """T9 · V4 es opcional: env REALESRGAN, datos/herramientas/realesrgan/ o el PATH. Sin ejecutable → None."""
    import os, shutil
    for c in (os.environ.get("REALESRGAN"), str(REALESRGAN), shutil.which("realesrgan-ncnn-vulkan")):
        if c and Path(c).is_file(): return c
    return None


def superres(img: Image.Image, exe: str | None = None, timeout: int = 180) -> Image.Image | None:
    """T9 · V4 = Real-ESRGAN (realesrgan-x4plus) y vuelta a ×2 con LANCZOS. None si no hay ejecutable o falla.
    Ojo: puede inventar dígitos nítidos → solo es una pasada más del voto, nunca sola."""
    import subprocess, tempfile
    exe = exe or _realesrgan_exe()
    if not exe: return None
    img = img.convert("RGB")
    with tempfile.TemporaryDirectory() as d:
        i, o = Path(d) / "i.png", Path(d) / "o.png"
        img.save(i)
        try:
            subprocess.run([exe, "-i", str(i), "-o", str(o), "-n", "realesrgan-x4plus", "-s", "4"], cwd=Path(exe).parent,
                           capture_output=True, timeout=timeout, check=True)
            out = Image.open(o).convert("RGB")
        except (OSError, subprocess.SubprocessError):
            return None
    return out.resize((img.width * 2, img.height * 2), Image.LANCZOS)


def variante(img: Image.Image, nombre: str) -> Image.Image | None:
    """Una sola variante por nombre (V0–V4). V4 = None si no hay Real-ESRGAN; nombre desconocido → ValueError."""
    if nombre == "V4": return superres(img)
    for n, v in variantes(img):
        if n == nombre: return v
    raise ValueError(f"variante desconocida: {nombre}")


def nitidez(img: Image.Image) -> dict:
    """C1: {'laplaciano': varianza del Laplaciano, 'tenengrad': media de |grad|^2 (Sobel)}. Más alto = más nítida.
    Se mide sobre un máximo de 1000 px de lado para que no dependa del tamaño de la foto."""
    import numpy as np
    g = ImageOps.grayscale(img)
    m = max(g.size)
    if m > 1000:
        g = g.resize((max(1, round(g.width * 1000 / m)), max(1, round(g.height * 1000 / m))), Image.BILINEAR)
    a = np.asarray(g, dtype=np.float64)
    if a.shape[0] < 3 or a.shape[1] < 3:
        return {"laplaciano": 0.0, "tenengrad": 0.0}
    c = a[1:-1, 1:-1]
    lap = a[:-2, 1:-1] + a[2:, 1:-1] + a[1:-1, :-2] + a[1:-1, 2:] - 4 * c
    gx = (a[:-2, 2:] + 2 * a[1:-1, 2:] + a[2:, 2:]) - (a[:-2, :-2] + 2 * a[1:-1, :-2] + a[2:, :-2])
    gy = (a[2:, :-2] + 2 * a[2:, 1:-1] + a[2:, 2:]) - (a[:-2, :-2] + 2 * a[:-2, 1:-1] + a[:-2, 2:])
    return {"laplaciano": float(lap.var()), "tenengrad": float((gx * gx + gy * gy).mean())}
