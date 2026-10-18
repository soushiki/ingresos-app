"""C4 · validar(doc, ctx): función pura (sin E/S) que dice por qué un recibo de venta es dudoso. R1 del plan.

Devuelve una lista de motivos legibles; lista vacía = validado. Dinero en pesos enteros.
ctx (todo opcional):
  tolerancia   pesos de diferencia aceptados en cada suma (por defecto 0)
  regla_items  False apaga «ítems → subtotal» (T2: la suma de ítems solo cuadra en ~72 % de los recibos de septiembre)
  esperados    números que trae el nombre de la foto (R5); `rango` (desde, hasta) sirve igual
  vecinos      los demás recibos de la misma foto (R5: montos idénticos con distinta mesa u hora)
"""
import re

CONFIG = {"tolerancia": 0, "regla_items": True}


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


def numeros_de_nombre(nombre: str) -> list | None:
    """«85560 al 565.jpg» → [85560…85565] · «85400 y 402 al 406» · «85627-628-629» · «comandas20260916_85627-628».
    Cualquier cosa rara (otras palabras, rango al revés o de más de 30, números muy lejanos) → None: sin R5 antes que avisos falsos."""
    base = re.split(r"[\\/]", nombre or "")[-1]
    base = re.sub(r"#\d+$", "", base); base = re.sub(r"\.[A-Za-z0-9]{2,4}$", "", base)
    base = re.sub(r"^[A-Za-z]*\d{8}_", "", base)
    out, prev, rango = [], None, False
    for t in re.findall(r"\d+|[^\W\d_]+", base.lower()):
        if t.isdigit():
            if prev is None and not 4 <= len(t) <= 6: return None
            n = int(t) if prev is None else _completar(t, prev, rango)
            if rango:
                if not 0 <= n - prev <= 30: return None
                out += range(prev + 1, n + 1); rango = False
            else: out.append(n)
            prev = n
        elif t == "al" and prev is not None and not rango: rango = True
        elif t not in _PALABRAS: return None
    if rango or not out or max(out) - min(out) > 100: return None
    return sorted(set(out))


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


def _digitos(doc: dict, vistos) -> list:
    """R3: número, total y pagado deben estar entre los números que vio Tesseract. vistos=None → se salta."""
    if vistos is None: return []
    g = lambda k: doc.get(k) or 0
    pedidos = [("el número de recibo", _num(doc), str), ("el total", g("consumo") + g("domicilio") + g("propina"), _p),
               ("lo pagado", g("pagado"), _p)]
    return [f"Tesseract no ve {et} ({f(n)}) en la imagen" for et, n, f in pedidos if n and n not in vistos]


def validar(doc: dict, ctx: dict | None = None) -> list:
    c = {**CONFIG, **(ctx or {})}; tol = c["tolerancia"]; m = []
    if doc.get("tipo", "venta") != "venta": return m
    g = lambda k: doc.get(k) or 0
    if not doc.get("numero"): m.append("Falta el número de recibo")
    if not doc.get("hora"): m.append("Falta la hora")
    if "mesa" not in (doc.get("detalle") or "").lower(): m.append("Falta la mesa")
    if not doc.get("medio"): m.append("Falta el medio de pago")
    esp = c.get("esperados") or (range(c["rango"][0], c["rango"][1] + 1) if c.get("rango") else None)
    if esp and _num(doc) is not None and _num(doc) not in set(esp):
        m.append(f"El recibo {_num(doc)} no está en el nombre de la foto ({_lista(esp)})")
    if c.get("vecinos"): m += cruces(doc, c["vecinos"])
    if doc.get("cortesia"): return m + _digitos(doc, c.get("digitos"))
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
    return m + _digitos(doc, c.get("digitos"))
