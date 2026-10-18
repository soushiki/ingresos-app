"""C4 · validar(doc, ctx): función pura (sin E/S) que dice por qué un recibo de venta es dudoso. R1 del plan.

Devuelve una lista de motivos legibles; lista vacía = validado. Dinero en pesos enteros.
ctx (todo opcional):
  tolerancia   pesos de diferencia aceptados en cada suma (por defecto 0)
  regla_items  False apaga «ítems → subtotal» (T2: la suma de ítems solo cuadra en ~72 % de los recibos de septiembre)
"""
CONFIG = {"tolerancia": 0, "regla_items": True}


def _p(n) -> str:
    return f"{int(n):,}".replace(",", ".")


def validar(doc: dict, ctx: dict | None = None) -> list:
    c = {**CONFIG, **(ctx or {})}; tol = c["tolerancia"]; m = []
    if doc.get("tipo", "venta") != "venta": return m
    g = lambda k: doc.get(k) or 0
    if not doc.get("numero"): m.append("Falta el número de recibo")
    if not doc.get("hora"): m.append("Falta la hora")
    if "mesa" not in (doc.get("detalle") or "").lower(): m.append("Falta la mesa")
    if not doc.get("medio"): m.append("Falta el medio de pago")
    if doc.get("cortesia"): return m
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
    return m
