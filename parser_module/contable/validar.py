"""C4 · validar(doc, ctx): función pura (sin E/S) que dice por qué un recibo de venta es dudoso. R1 del plan.

Devuelve una lista de motivos legibles; lista vacía = validado. Dinero en pesos enteros.
ctx (todo opcional):
  tolerancia   pesos de diferencia aceptados en cada suma (por defecto 0)
  regla_items  True enciende «ítems → subtotal»; apagada por defecto (T2: la suma de ítems solo cuadra en ~72 % de los recibos de septiembre)
  esperados    números que trae el nombre de la foto (R5); `rango` (desde, hasta) sirve igual
  digitos      números que vio Tesseract (R3b): leer otro número del nombre → motivo; no verlo → nota (notas_digitos); None/ausente se salta
  catalogo     {PRODUCTO: precio unitario} de catalogo.cargar() (R6); ausente/vacío se salta
  vecinos      los demás recibos de la misma foto (R5: montos idénticos con distinta mesa u hora)
"""
import re
import unicodedata
from typing import NamedTuple

CONFIG = {"tolerancia": 0, "regla_items": False}


def _p(n) -> str:
    return f"{int(n):,}".replace(",", ".")


_PALABRAS = {"al", "y", "a", "rappi", "comanda", "comandas"}
MONTOS = ("subtotal", "descuento", "consumo", "domicilio", "propina", "pagado", "cambio")
FALTA = "Falta el recibo {} en esta foto"


def _completar(t: str, prev: int, en_rango: bool) -> int:
    """«565» después de 85560 → 85565 (el nombre abrevia con los dígitos del anterior)."""
    s = str(prev)
    if len(t) >= len(s): return int(t)
    n = int(s[:len(s) - len(t)] + t)
    return n + 10 ** len(t) if en_rango and n < prev else n


class Nombre(NamedTuple):
    """ADR-009 · numeros: lista o None · correcciones: ["3341 → 85341"] · entendido: False si trae un número de recibo que no se pudo leer."""
    numeros: list | None
    correcciones: list
    entendido: bool


def _por_sufijo(t: str, prev: int) -> int | None:
    """ADR-009: «3341» tras 85338 cae fuera de rango; sus últimas k−1, k−2 … (≥ 2) cifras completadas con el anterior, la primera en rango gana."""
    if len(t) >= len(str(prev)): return None
    for k in range(len(t) - 1, 1, -1):
        n = _completar(t[-k:], prev, True)
        if 0 <= n - prev <= 30: return n
    return None


def leer_nombre(nombre: str) -> Nombre:
    """«85560 al 565.jpg» → [85560…85565] · «85400 y 402 al 406» · «85627-628-629» · «comandas20260916_85627-628».
    Un fin de rango acortado fuera de rango se corrige por sufijo y queda en `correcciones` (ADR-009).
    Cualquier cosa rara (otras palabras, rango al revés o de más de 30, números muy lejanos) → numeros None: sin R5 antes que avisos falsos.
    `entendido` es False solo si el nombre empieza por un número de recibo (4–6 cifras) y aun así no se pudo leer; nombres de
    escáner, cámara o fecha («comandas20261002_15584574», «IMG_…», «COMANDAS 2026-09-15») → Nombre(None, [], True), sin marcador."""
    base = re.split(r"[\\/]", nombre or "")[-1]
    base = re.sub(r"#\d+$", "", base); base = re.sub(r"\.[A-Za-z0-9]{2,4}$", "", base)
    base = re.sub(r"^[A-Za-z]*\d{8}_", "", base)
    if re.search(r"\d{7}|\d{4}-\d{2}-\d{2}", base): return Nombre(None, [], True)
    malo = Nombre(None, [], not re.match(r"\d{4,6}(?!\d)", base))
    out, prev, rango, corr = [], None, False, []
    for t in re.findall(r"\d+|[^\W\d_]+", base.lower()):
        if t.isdigit():
            if prev is None and not 4 <= len(t) <= 6: return malo
            n = int(t) if prev is None else _completar(t, prev, rango)
            if rango:
                if not 0 <= n - prev <= 30:
                    n2 = _por_sufijo(t, prev)
                    if n2 is None: return malo
                    corr.append(f"{t} → {n2}"); n = n2
                out += range(prev + 1, n + 1); rango = False
            else: out.append(n)
            prev = n
        elif t == "al" and prev is not None and not rango: rango = True
        elif t not in _PALABRAS: return malo
    if rango or not out or max(out) - min(out) > 100: return malo
    return Nombre(sorted(set(out)), corr, True)


def numeros_de_nombre(nombre: str) -> list | None:
    """Envoltorio de leer_nombre: solo los números (None si no se entiende)."""
    return leer_nombre(nombre).numeros


def rango_de_nombre(nombre: str) -> tuple | None:
    """«85560 al 565» → (85560, 85565)."""
    ns = numeros_de_nombre(nombre)
    return (ns[0], ns[-1]) if ns else None


def _lista(nums) -> str:
    ns = sorted(set(nums)); grupos = [[ns[0]]]
    for n in ns[1:]:
        if n == grupos[-1][-1] + 1: grupos[-1].append(n)
        else: grupos.append([n])
    return ", ".join(f"{g[0]} al {g[-1]}" if len(g) > 2 else ", ".join(map(str, g)) for g in grupos)


def _num(d) -> int | None:
    n = str(d.get("numero") or "")
    return int(n) if n.isdigit() else None


def faltantes(docs: list, esperados) -> list:
    """Números del nombre de la foto que no salió en ningún recibo de venta leído."""
    leidos = {_num(d) for d in docs if d.get("tipo") == "venta"}
    return sorted(set(esperados or ()) - leidos)


def _mesa(d) -> str:
    m = re.search(r"mesa\s*:?\s*(\S+)", d.get("detalle") or "", re.I)
    return m.group(1).lower() if m else ""


def cruces(doc: dict, vecinos: list) -> list:
    """R5: el mismo juego de montos que otro recibo de la foto, con distinta mesa u hora → el OCR pudo cruzar valores."""
    if not doc.get("consumo"): return []
    k = tuple(doc.get(x) or 0 for x in MONTOS); out = []
    for v in vecinos:
        if v is doc or v.get("tipo", "venta") != "venta" or (_num(v) is not None and _num(v) == _num(doc)): continue
        if tuple(v.get(x) or 0 for x in MONTOS) == k and (_mesa(v) != _mesa(doc) or (v.get("hora") or "") != (doc.get("hora") or "")):
            out.append(f"Mismos montos que el recibo {v.get('numero') or '(sin número)'} con distinta mesa u hora: posible cruce de valores")
    return out


def _pedidos(doc: dict) -> list:
    g = lambda k: doc.get(k) or 0
    return [("el número de recibo", _num(doc), str), ("el total", g("consumo") + g("domicilio") + g("propina"), _p),
            ("lo pagado", g("pagado"), _p)]


def notas_digitos(doc: dict, ctx: dict | None) -> list:
    """R3b · nota suave (NO motivo): número, total o pagado que Tesseract no ve. ctx["digitos"]=None/ausente → sin notas."""
    vistos = (ctx or {}).get("digitos")
    if vistos is None or doc.get("tipo", "venta") != "venta": return []
    return [f"Sin confirmar por segundo lector: {et} ({f(n)})" for et, n, f in _pedidos(doc) if n and n not in vistos]


def _digitos(doc: dict, vistos, esperados=None) -> list:
    """R3b · «dudoso» solo si Tesseract lee OTRO número con contexto: el número de recibo no aparece pero sí otro número del nombre
    de la foto (R5). No verlo es solo nota (notas_digitos). vistos=None → se salta."""
    n = _num(doc)
    if vistos is None or not n or n in vistos: return []
    otros = sorted(set(esperados or ()) & set(vistos) - {n})
    return [f"Tesseract lee el recibo {otros[0]} y no el {n} en la imagen"] if otros else []


def _carta(doc: dict, precios) -> list:
    """R6: precio ≠ carta → dudoso; línea sin precio → se SUGIERE el de la carta (aviso, no reemplaza nada). precios=None/vacío → se salta."""
    if not precios: return []
    from .catalogo import clave, unitario, sugerencias
    m = []
    for i in doc.get("items") or []:
        k, u = clave(i.get("nombre")), unitario(i)
        if k in precios and u is not None and u != precios[k]:
            m.append(f"{k} cuesta {_p(u)} en el recibo y {_p(precios[k])} en la carta")
    m += [f"Línea ilegible «{k}»: precio sugerido por la carta {_p(v)}" for _, k, v in sugerencias(doc, precios)]
    return m


def validar(doc: dict, ctx: dict | None = None) -> list:
    c = {**CONFIG, **(ctx or {})}; tol = c["tolerancia"]; m = []
    if doc.get("tipo", "venta") != "venta": return m
    g = lambda k: doc.get(k) or 0
    if not doc.get("numero"): m.append("Falta el número de recibo")
    if not doc.get("hora"): m.append("Falta la hora")
    det = unicodedata.normalize("NFD", (doc.get("detalle") or "").lower()).encode("ascii", "ignore").decode()
    if "mesa" not in det and not g("domicilio") > 0 and "domicilio" not in det and "llevar" not in det: m.append("Falta la mesa")
    if not doc.get("medio"): m.append("Falta el medio de pago")
    esp = c.get("esperados") or (range(c["rango"][0], c["rango"][1] + 1) if c.get("rango") else None)
    if esp and _num(doc) is not None and _num(doc) not in set(esp):
        m.append(f"El recibo {_num(doc)} no está en el nombre de la foto ({_lista(esp)})")
    if c.get("vecinos"): m += cruces(doc, c["vecinos"])
    if doc.get("cortesia"): return m + _digitos(doc, c.get("digitos"), esp) + _carta(doc, c.get("catalogo"))
    items, sub = doc.get("items") or [], g("subtotal")
    if c["regla_items"] and items and sub:
        s = sum(i.get("valor", 0) for i in items)
        if abs(s - sub) > tol: m.append(f"Los ítems suman {_p(s)} y el subtotal dice {_p(sub)}")
    if sub and abs(sub - g("descuento") - g("consumo")) > tol:
        m.append(f"Subtotal {_p(sub)} − descuento {_p(g('descuento'))} no da el consumo {_p(g('consumo'))}")
    pagado = g("pagado")
    if pagado:
        esperado = g("consumo") + g("domicilio") + g("propina")
        if abs(pagado - g("cambio") - esperado) > tol:
            m.append(f"Pagado {_p(pagado)} − cambio {_p(g('cambio'))} no da consumo + domicilio + propina ({_p(esperado)})")
        medios = g("efectivo") + g("tarjeta") + g("transf") + g("credito")
        if abs(pagado - g("cambio") - medios) > tol:
            m.append(f"Los medios de pago suman {_p(medios)} y pagado − cambio es {_p(pagado - g('cambio'))}")
    return m + _digitos(doc, c.get("digitos"), esp) + _carta(doc, c.get("catalogo"))
