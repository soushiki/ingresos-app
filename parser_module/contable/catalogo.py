"""R6 · Catálogo de precios (la carta) armado desde los recibos «validado»/«revisado» y editable a mano.

`datos/catalogo.json` = {"auto": {producto: precio unitario}, "manual": {producto: precio}}.
«auto» se rehace con `reconstruir`; «manual» no se toca nunca y gana sobre «auto». Dinero en pesos enteros.
`validar` solo recibe el dict ya resuelto (`precios`) por ctx["catalogo"]; aquí está la E/S.
"""
import json
import os
import re
from collections import Counter

from .asientos import estado_de

RUTA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "datos", "catalogo.json")


def clave(nombre) -> str:
    """«  Jugo  de Mora » → «JUGO DE MORA»."""
    return re.sub(r"\s+", " ", str(nombre or "")).strip().upper()


def unitario(item: dict) -> int | None:
    """Precio de una unidad (valor ÷ cantidad) si la línea se lee completa y reparte exacto; si no, None."""
    cant, valor = item.get("cant") or 1, item.get("valor") or 0
    return valor // cant if valor > 0 and cant > 0 and valor % cant == 0 else None


def construir(docs) -> dict:
    """Precio más frecuente por producto, solo con ventas validadas o revisadas."""
    vistos: dict = {}
    for d in docs:
        if d.get("tipo", "venta") != "venta" or estado_de(d) not in ("validado", "revisado"): continue
        for i in d.get("items") or []:
            k, u = clave(i.get("nombre")), unitario(i)
            if k and u: vistos.setdefault(k, Counter())[u] += 1
    return {k: c.most_common(1)[0][0] for k, c in sorted(vistos.items())}


def cargar(ruta: str = RUTA) -> dict:
    """Precios resueltos (manual sobre auto). Sin archivo o ilegible → {} (R6 no hace nada)."""
    try:
        with open(ruta, encoding="utf-8") as f: j = json.load(f)
        return {**{clave(k): int(v) for k, v in (j.get("auto") or {}).items()},
                **{clave(k): int(v) for k, v in (j.get("manual") or {}).items()}}
    except (OSError, ValueError, AttributeError, TypeError):
        return {}


def reconstruir(docs, ruta: str = RUTA) -> dict:
    """Rehace «auto» desde los documentos; conserva «manual». Devuelve los precios resueltos."""
    manual = {}
    try:
        with open(ruta, encoding="utf-8") as f: manual = json.load(f).get("manual") or {}
    except (OSError, ValueError, AttributeError): pass
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump({"auto": construir(docs), "manual": manual}, f, ensure_ascii=False, indent=1, sort_keys=True)
    return cargar(ruta)


def desde_libro(libro: dict, ruta: str = RUTA) -> dict:
    """libro = {fecha: {"documentos": [...]}} (el de libro.json)."""
    return reconstruir([d for v in (libro or {}).values() for d in v.get("documentos", [])], ruta)


def sugerencias(doc: dict, precios) -> list:
    """Líneas ilegibles (producto conocido, sin valor) → [(indice, nombre, precio_unitario × cant)]. Nunca modifica el doc."""
    out = []
    for n, i in enumerate(doc.get("items") or []):
        k = clave(i.get("nombre"))
        if k in (precios or {}) and not i.get("valor"): out.append((n, k, precios[k] * (i.get("cant") or 1)))
    return out
