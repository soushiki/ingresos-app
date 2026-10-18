"""C6 · ADR-006: recortes de recibos en disco, un JPEG gris por huella (sha256[:16]). Solo este módulo escribe y borra en la carpeta."""
from __future__ import annotations
import hashlib, io, re
from datetime import date, datetime
from pathlib import Path

NOMBRE = re.compile(r"^[0-9a-f]{16}\.jpg$")


def guardar(img, carpeta) -> str:
    """Guarda el recorte (PIL) como JPEG gris y devuelve su nombre. La misma imagen da el mismo nombre y no duplica archivo."""
    buf = io.BytesIO(); img.convert("L").save(buf, "JPEG", quality=80)
    datos = buf.getvalue()
    nombre = hashlib.sha256(datos).hexdigest()[:16] + ".jpg"
    carpeta = Path(carpeta); carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / nombre
    if not ruta.exists(): ruta.write_bytes(datos)
    return nombre


def abrir(nombre, carpeta) -> bytes | None:
    """Bytes del recorte, o None si el nombre no cumple el patrón o no existe."""
    if not isinstance(nombre, str) or not NOMBRE.fullmatch(nombre): return None
    ruta = Path(carpeta) / nombre
    return ruta.read_bytes() if ruta.is_file() else None


def borrar(desde: date, hasta: date, carpeta) -> int:
    """Borra los recortes cuya fecha de guardado cae en [desde, hasta]. Devuelve cuántos."""
    n = 0
    for p in Path(carpeta).glob("*.jpg"):
        if not NOMBRE.fullmatch(p.name): continue
        if desde <= datetime.fromtimestamp(p.stat().st_mtime).date() <= hasta: p.unlink(); n += 1
    return n


def huerfanos(usados, carpeta) -> list[str]:
    """Nombres en disco que ningún documento usa (`usados`: iterable de nombres)."""
    usados = set(usados)
    return sorted(p.name for p in Path(carpeta).glob("*.jpg") if NOMBRE.fullmatch(p.name) and p.name not in usados)
