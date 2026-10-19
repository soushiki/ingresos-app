"""Documentos del día → filas del libro (débito/crédito) con tus cuentas y tus frases."""
from __future__ import annotations
import json, re
from collections import Counter, defaultdict
from pathlib import Path

AQUI = Path(__file__).parent
CATALOGO = {c["codigo"]: c for c in json.loads((AQUI / "plan_de_cuentas.json").read_text(encoding="utf8"))}
EFECTIVO, BANCO, RESTAURANTE, DOMICILIOS, PROPINAS = "11050501", "11200501", "41401501", "28150501", "28150502"
POR_COBRAR, CXC_CLIENTES = "13452501", "13050501"
# casillas «Recaudos del banco» (de tu extracto): clave → (descripción, medio). «rappi» va aparte: es el pago de lo que Rappi te debía.
RECAUDOS_BANCO = [("llave", "Recaudos a través de LLAVE", "Bre-B"), ("tarjetas", "Recaudos con tarjetas", "Tarjeta"), ("qr", "Recaudos a través de QR", "QR"),
                  ("nequi", "Recaudos a través de Transferencia Nequi", "Nequi"), ("transferencias", "Recaudos por transferencias", "Transferencia"),
                  ("pse", "Recaudos por PSE", "PSE")]
RECAUDO_DESC = {m: d for _, d, m in RECAUDOS_BANCO} | {"App": "Ventas por Rappi", "Crédito personal": "Venta a crédito personal",
                                                       "Daviplata": "Recaudos a través de Daviplata"}
# puente_*: adonde va lo que no se pudo leer (venta sin medio, gasto sin cuenta), para que nada se descarte en silencio (R10).
# Códigos PUC 138095 «Deudores varios – otros» y 519595 «Gastos diversos – otros»; cámbialos en contable.json si tu contador usa otros.
CFG = {"reporta_efectivo": "Yorly", "reporta_banco": "Sergio", "cuenta_recaudo": "", "puente_ingreso": "13809501", "puente_gasto": "51959501", "salto_comanda": 30}
PUENTES = {"13809501": "Puente ingreso: venta sin medio de pago", "51959501": "Puente gasto: gasto sin cuenta"}


def nombre(cod: str) -> str:
    return CATALOGO.get(cod, {}).get("nombre_diario") or PUENTES.get(cod) or ("SIN CLASIFICAR" if not cod else cod)


def abreviar_recibos(nums) -> str:
    """85531, 85533, 85534 → «85531, 533, 534» (como los escribes en la descripción)."""
    n = sorted({str(x) for x in nums if str(x).strip()}, key=lambda s: (len(s), s))
    if not n: return ""
    return ", ".join([n[0]] + [x[-3:] if len(x) == len(n[0]) and x[:-3] == n[0][:-3] else x for x in n[1:]])


def rangos(nums) -> str:
    """210, 211, 212, 213 → «210 al 213» · 208, 209, 214 → «208, 209 y 214»."""
    v = sorted({int(x) for x in nums if str(x).strip().isdigit()}); grupos, g = [], []
    for x in v:
        if g and x == g[-1] + 1: g.append(x)
        else:
            if g: grupos.append(g)
            g = [x]
    if g: grupos.append(g)
    partes = []
    for g in grupos: partes += [f"{g[0]} al {g[-1]}"] if len(g) >= 3 else [str(x) for x in g]
    return partes[0] if len(partes) == 1 else ", ".join(partes[:-1]) + " y " + partes[-1] if partes else ""


def datos_cierre(docs: list) -> dict:
    """Cifras del cierre del día: lo que leyeron los papeles de tipo «cierre» (el primer valor distinto de cero de cada una)."""
    out = {}
    for d in docs:
        if d.get("tipo") == "cierre":
            for k, v in (d.get("datos") or {}).items():
                if v and not out.get(k): out[k] = v
    return out


def repartir(d: dict) -> dict:
    """¿Con qué se pagó cada cosa de una comanda? Lo electrónico (tarjeta, transferencia, app) cubre primero el consumo,
    luego el domicilio y al final la propina; lo que falte lo puso el efectivo. Solo la propina y el domicilio que se
    pagaron en efectivo entran al bloque de efectivo de la caja. «Electrónico» incluye el crédito personal (fiado)."""
    elec = d.get("tarjeta", 0) + d.get("transf", 0) + d.get("credito", 0)
    cons_e = min(elec, d.get("consumo", 0)); resto = elec - cons_e
    dom_e = min(resto, d.get("domicilio", 0)); p_e = max(0, min(resto - dom_e, d.get("propina", 0)))
    tip_t = round(p_e * d.get("tarjeta", 0) / elec) if elec else 0
    tip_c = round(p_e * d.get("credito", 0) / elec) if elec else 0
    return dict(cons_e=cons_e, dom_e=dom_e, tip_e=p_e, tip_tarjeta=tip_t, tip_transf=p_e - tip_t - tip_c, tip_credito=tip_c,
                cash_cons=d.get("consumo", 0) - cons_e, cash_dom=d.get("domicilio", 0) - dom_e, cash_tip=d.get("propina", 0) - p_e,
                tarjeta_cons=d.get("tarjeta", 0) - tip_t)


def completar_desde_cierre(docs: list) -> list:
    """Los vales manuscritos casi nunca se leen; el cierre del POS trae «GASTOS DETALLADOS» con el nombre de cada gasto.
    Si un gasto no tiene descripción, se toma de ahí por el valor."""
    det = [(n, v) for d in docs if d.get("tipo") == "cierre" for n, v in (d.get("gastos_detalle") or [])]
    usados = set()
    for d in docs:
        if d.get("tipo") in ("gasto_caja", "caja_menor_manuscrito") and not (d.get("detalle") or "").strip() and d.get("valor"):
            k = next((x for x, (n, v) in enumerate(det) if v == d["valor"] and x not in usados), None)
            if k is not None:
                usados.add(k); d["detalle"] = det[k][0].title(); d.setdefault("avisos", []).append("Descripción tomada de «Gastos detallados» del cierre")
    return docs


def faltantes(docs: list, c: dict) -> list:
    """Números de comanda que el rango Factura inicial → final del cierre incluye y no hay papel."""
    ini, fin = c.get("factura_inicial", 0), c.get("factura_final", 0)
    if not (ini and fin and 0 < fin - ini < 500): return []
    hay = {int(d["numero"]) for d in docs if d.get("tipo") == "venta" and str(d.get("numero", "")).isdigit()}
    return [n for n in range(ini, fin + 1) if n not in hay]


def fuera_de_secuencia(docs: list, salto: int) -> list:
    """M-4: comandas cuyo número queda a más de `salto` de cualquier otra comanda del día (con 3 o más números distintos).
    Suele ser un papel de otro día que trae otra fecha escrita (reimpresión) o un número mal leído (65310 por 85310)."""
    ns = sorted({int(d["numero"]) for d in docs if d.get("tipo") == "venta" and str(d.get("numero", "")).isdigit()})
    if len(ns) < 3: return []
    return [n for i, n in enumerate(ns) if min(abs(n - m) for m in ns[max(i - 1, 0):i] + ns[i + 1:i + 2]) > salto]


def cruzar(docs: list, c: dict) -> tuple:
    """¿Lo que dice el cierre del POS coincide con la suma de tus comandas y gastos? Una diferencia = falta un papel o se leyó mal.
    Devuelve (filas del cruce, números de comanda que faltan)."""
    if not c: return [], []
    v = [d for d in docs if d["tipo"] == "venta" and d.get("contar")]
    g = [d for d in docs if d["tipo"] in ("gasto_caja", "caja_menor_manuscrito") and d.get("contar") and d["medio"] in ("", "Efectivo")]
    R = [repartir(d) for d in v]
    falta = faltantes(docs, c)
    filas = [("Venta total (sin domicilios ni propinas)", c.get("total_vendido", 0), sum(d["consumo"] for d in v)),
             ("Venta en efectivo (sin propina)", c.get("venta_efectivo", 0), sum(r["cash_cons"] + r["cash_dom"] for r in R)),
             ("Tarjetas (sin propina)", c.get("tarjetas_sin_prop", 0), sum(r["tarjeta_cons"] for r in R)),
             ("Transferencias / app (con propina)", c.get("transferencias", 0), sum(d["transf"] for d in v)),
             ("Propinas (total)", c.get("propinas_total", 0), sum(d["propina"] for d in v)),
             ("Propinas en efectivo", c.get("propinas_efectivo", 0), sum(r["cash_tip"] for r in R)),
             ("Domicilios cobrados", c.get("domicilios_pagados", 0), sum(d["domicilio"] for d in v)),
             ("Descuentos y cortesías", c.get("descuentos", 0), sum(d["descuento"] for d in v)),
             ("Gastos de caja", c.get("gastos_caja", 0), sum(d["valor"] for d in g))]
    out = [dict(concepto=n, cierre=a, papeles=b, diferencia=a - b, ok=abs(a - b) <= 1) for n, a, b in filas if (a or b) and not (n in ("Gastos de caja",) and not a)]
    if c.get("transacciones"):
        n_ok = len(v) == c["transacciones"]
        out.append(dict(concepto="Número de comandas", cierre=c["transacciones"], papeles=len(v), diferencia=c["transacciones"] - len(v), ok=n_ok,
                        nota="" if n_ok else ("Falta la comanda " + ", ".join(map(str, falta)) if falta else "Revisa si hay comandas repetidas o de más")))
    return out, falta


def firma_venta(d: dict) -> tuple:
    """M-8: (hora de «Fecha de Venta», mesa) de una comanda, leídas del texto; "" si no se leyó."""
    t = (d.get("texto") or "").lower()
    h = re.search(r"fecha de venta\W*\S+\s+(\d{1,2}:\d{2}(?::\d{2})?\s*[ap]\W*m)", t)
    m = re.search(r"mesa\s*:?\s*([a-z0-9]+)", t) or re.search(r"mesa\s+([a-z0-9]+)", (d.get("detalle") or "").lower())
    return (re.sub(r"\W", "", h.group(1)) if h else "", m.group(1) if m else "")


def misma_venta(a: dict, b: dict) -> bool:
    """Dos comandas son el mismo papel (foto cargada dos veces) solo si los datos coinciden de verdad: el texto es idéntico, o la hora
    de «Fecha de Venta» y la mesa se leyeron en las dos y son iguales y los valores no se contradicen. Un dato sin leer NO es
    coincidencia: papeles distintos cuentan aunque compartan número o no se lea el número (M-8). Un valor 0 cuenta como «no leído»."""
    if a.get("texto") and a.get("texto") == b.get("texto"): return True
    (ha, ma), (hb, mb) = firma_venta(a), firma_venta(b)
    if not (ha and ma and ha == hb and ma == mb): return False
    total = lambda d: d.get("efectivo", 0) + d.get("tarjeta", 0) + d.get("transf", 0) + d.get("credito", 0)
    return all(not x or not y or x == y for x, y in ((a.get("consumo", 0), b.get("consumo", 0)), (total(a), total(b))))


def numeros_repetidos(docs: list) -> dict:
    """M-8: número de comanda → cuántas comandas que cuentan lo comparten (recibos distintos con el mismo número leído)."""
    c = Counter(d["numero"] for d in docs if d.get("tipo") == "venta" and d.get("numero") and d.get("contar"))
    return {n: k for n, k in c.items() if k > 1}


def marcar_duplicados(docs: list) -> list:
    """El gasto de caja impreso y su «recibo de caja menor» manuscrito son el MISMO gasto: se cuenta uno solo.
    Una comanda es duplicada solo si es el mismo papel (misma_venta): con número, frente a las de su número; sin número, frente a todas. En cada pasada se borra el «duplicado de»
    anterior (si el número se corrigió, vuelve a contar), salvo que tú hayas marcado a mano si cuenta (manual_contar)."""
    for d in docs:
        if d.get("tipo") in ("gasto_caja", "venta") and not d.get("manual_contar"): d["dup_de"] = ""
    vistos, ventas = {}, {}
    for d in docs:
        if d.get("tipo") == "gasto_caja" and d.get("numero"):
            if d["numero"] in vistos: d["dup_de"] = vistos[d["numero"]]
            else: vistos[d["numero"]] = d["id"]
        if d.get("tipo") == "venta" and d.get("numero"):
            igual = next((o for o in ventas.get(d["numero"], []) if misma_venta(o, d)), None)
            if igual: d["dup_de"] = igual["id"]
            else: ventas.setdefault(d["numero"], []).append(d)
    for d in docs:   # sin número: se compara con todas las comandas que quedaron (con o sin número)
        if d.get("tipo") == "venta" and not d.get("numero"):
            igual = next((o for vs in ventas.values() for o in vs if misma_venta(o, d)), None)
            if igual: d["dup_de"] = igual["id"]
            else: ventas.setdefault("", []).append(d)
    impresos = {(x["valor"], x["id"]) for x in docs if x.get("tipo") == "gasto_caja" and not x.get("dup_de")}
    usados = set()
    for d in docs:
        if d.get("tipo") == "caja_menor_manuscrito":
            par = next(((v, i) for v, i in sorted(impresos) if v == d.get("valor") and i not in usados), None)
            if par: usados.add(par[1]); d["dup_de"] = par[1]
            else: d["dup_de"] = ""
    for d in docs:
        if not d.get("manual_contar"): d["contar"] = not d.get("dup_de") and d.get("tipo") not in ("otro", "cierre", "faltante")
    return docs


FALTA_CUENTA = "falta la cuenta"   # aviso de DATOS OCR que construir() reconoce (DEBT-1)
COLS_DATOS = ["fecha", "archivo", "tipo", "numero", "tercero", "detalle", "valor", "medio", "cuenta", "estado", "aviso", "propina", "domicilio", "bloque", "id", "recibo", "motivo"]   # T12: recibo = validado|dudoso|revisado (estado_de) y motivo = por qué es dudoso (R7)


def datos_ocr(fecha: str, todos: list, banco: dict, cfg: dict) -> list:
    """Hoja DATOS OCR (R9, ADR-002): una fila por papel y medio de pago, también los que no cuentan (duplicados, cierre)
    o van a puente, para que se vea qué se leyó y de dónde sale cada cifra. `todos` ya pasó por marcar_duplicados.
    estado: ok (suma) · no cuenta · en extracto (lo cubre el extracto bancario) · pendiente (sin valor leído).
    bloque: venta · caja · factura · extracto · rappi, el asiento al que va la fila."""
    datos = []
    def dato(d=None, **k):
        r = dict(fecha=fecha, archivo="", tipo="", numero="", tercero="", detalle="", valor=0, medio="", cuenta="", estado="ok", aviso="", propina=0, domicilio=0, bloque="", id="", recibo="", motivo="")
        if d: r.update(recibo=estado_de(d), motivo="; ".join(d.get("motivos") or d.get("avisos") or []) if estado_de(d) == "dudoso" else "",   # FIX-13: solo el dudoso trae motivo
                         archivo=d.get("origen", ""), tipo=d["tipo"], numero=d.get("numero", ""), tercero=d.get("tercero", ""), detalle=d.get("detalle", ""), id=d["id"])
        r.update(k); datos.append(r)
    for k, desc, medio in RECAUDOS_BANCO:
        if int(banco.get(k) or 0): dato(tipo="extracto", archivo="extracto bancario", detalle=desc, valor=int(banco[k]), medio=medio, cuenta=BANCO, bloque="extracto")
    if int(banco.get("rappi") or 0): dato(tipo="extracto", archivo="extracto bancario", detalle="Pagos interbancarios Rappi", valor=int(banco["rappi"]), medio="Transferencia", cuenta=BANCO, bloque="rappi")
    en_ext = any(int(banco.get(k) or 0) for k, _, _ in RECAUDOS_BANCO)
    for d in todos:
        if d["tipo"] == "faltante": continue   # ADR-008: el marcador no es un papel leído; no tiene fila en DATOS OCR
        if not d.get("contar") or d["tipo"] == "cierre":
            dato(d, valor=d.get("valor") or d.get("consumo") or 0, estado="no cuenta",
                 aviso=f"duplicado de {d['dup_de']}" if d.get("dup_de") else ("cierre de caja (se usa para cruzar)" if d["tipo"] == "cierre" else (d.get("motivo") or "desmarcado")))
        elif d["tipo"] == "venta":
            n0 = len(datos); r = repartir(d); tot = d.get("tarjeta", 0) + d.get("transf", 0) + d.get("credito", 0)
            if d["efectivo"] or r["cash_tip"] or r["cash_dom"]:   # con valor 0 si solo la propina se dio en efectivo, para que el tope del efectivo se vea
                dato(d, tercero="Consumidor Final", valor=d["efectivo"], medio="Efectivo", cuenta=EFECTIVO, propina=r["cash_tip"], domicilio=r["cash_dom"], bloque="venta")
            partes = []
            if d.get("tarjeta"): partes.append((BANCO, "Consumidor Final", "Tarjeta", d["tarjeta"], en_ext))
            if d.get("transf"):
                m = d.get("medio_transf") or "Transferencia"
                partes.append((POR_COBRAR, "Rappi", "App", d["transf"], False) if m == "Rappi" else (BANCO, "Consumidor Final", m, d["transf"], en_ext))
            if d.get("credito"): partes.append((CXC_CLIENTES, d.get("cliente") or "Cliente (crédito personal)", "Crédito personal", d["credito"], False))
            for cod, ter, medio, v, ext in partes:   # la propina y el domicilio no pagados en efectivo se reparten según lo que puso cada medio (como en construir)
                dato(d, tercero=ter, valor=v, medio=medio, cuenta=cod, estado="en extracto" if ext else "ok", aviso="lo cubre el extracto bancario" if ext else "",
                     propina=round(r["tip_e"] * v / tot), domicilio=round(r["dom_e"] * v / tot), bloque="venta")
            if d.get("consumo") and not d.get("cortesia") and not tot + d["efectivo"]:
                dato(d, tercero="Consumidor Final", valor=d["consumo"], medio="(sin medio)", cuenta=cfg["puente_ingreso"], aviso="no se leyó con qué se pagó; corrige el medio", bloque="venta")
            if len(datos) == n0:   # no se leyó ninguna cifra: no tiene asiento, pero el papel se ve para corregirlo
                dato(d, estado="no cuenta" if d.get("cortesia") else "pendiente", aviso="cortesía" if d.get("cortesia") else "no se leyó el valor de la venta", bloque="venta")
        elif d["tipo"] in ("gasto_caja", "caja_menor_manuscrito") and d["medio"] in ("", "Efectivo"):
            dato(d, valor=d["valor"], medio="Efectivo", cuenta=d.get("cuenta") or cfg["puente_gasto"], aviso="" if d.get("cuenta") else FALTA_CUENTA, bloque="caja")
        elif d["tipo"] in ("factura", "gasto_caja", "caja_menor_manuscrito"):
            dato(d, valor=d["valor"], medio=d["medio"], cuenta=d["cuenta"] or cfg["puente_gasto"], estado="ok" if d["valor"] else "pendiente",
                 aviso="; ".join(a for a in ("" if d["valor"] else "sin valor leído", "" if d["cuenta"] else FALTA_CUENTA) if a), bloque="factura")
        else:
            dato(d, valor=d.get("valor") or 0, estado="no cuenta", aviso="tipo de papel sin asiento")
    return datos


def estado_de(d: dict) -> str:
    """Estado del recibo: validado | dudoso | revisado (03 §4). Migración al leer, sin tocar el documento: sin `estado`, el viejo
    `revisado: true` pasa a «revisado»; si no, «validado» sin avisos y «dudoso» con avisos."""
    if d.get("estado") in ("validado", "dudoso", "revisado"): return d["estado"]
    return "revisado" if d.get("revisado") else "dudoso" if d.get("avisos") else "validado"


def construir(fecha: str, docs: list, banco: dict | None = None, cfg: dict | None = None, cierre: dict | None = None) -> dict:
    cfg = {**CFG, **{k: v for k, v in (cfg or {}).items() if v not in (None, "")}}; banco = banco or {}; filas, avisos, pendientes = [], [], []
    todos = marcar_duplicados(docs); completar_desde_cierre(todos)
    docs = [d for d in todos if d.get("contar") and d["tipo"] != "cierre"]
    datos = datos_ocr(fecha, todos, banco, cfg)
    cie = {**datos_cierre(todos), **{k: int(v) for k, v in (cierre or {}).items() if v is not None}}
    # R1 (ajuste al cierre): el cierre del POS manda sobre los papeles. Solo con total vendido leído y fecha del cierre (o cifras escritas a mano).
    # Si el cierre supera la venta de los papeles (consumo, sin propina ni domicilio) la diferencia entra al puente 13809501; si no, solo avisa.
    ajuste = 0; fecha_cierre = bool(cierre) or any(d.get("tipo") == "cierre" and d.get("fecha") == fecha for d in todos)
    if cie.get("total_vendido") and fecha_cierre:
        en_papeles = sum(d["consumo"] for d in todos if d["tipo"] == "venta" and d.get("contar"))
        dif = cie["total_vendido"] - en_papeles
        if dif > 1:
            ajuste = dif; j_aj = len(datos)
            datos.append(dict(fecha=fecha, archivo="cierre de caja", tipo="cierre", numero="", tercero="Consumidor Final", detalle="Ajuste al cierre (cierre > papeles)", valor=ajuste, medio="",
                              cuenta=cfg["puente_ingreso"], estado="ok", aviso="total vendido del cierre − consumo de las comandas", propina=0, domicilio=0, bloque="cierre", id="", recibo="", motivo=""))
    # R2 (débito 2815 desde el cierre): lo que el cierre dice que se pagó en propinas y domicilios baja el pasivo. Los vales «pago domicilios»
    # ya debitan 28150501 desde la caja menor: del cierre solo sale la parte que ellos no cubrieron (nunca negativa, nunca dos veces).
    j_pro = j_dom = None; pago_pro = pago_dom = 0
    if fecha_cierre:
        pago_pro = max(cie.get("propinas_total", 0), 0)
        en_vales = sum(d["valor"] for d in todos if d.get("contar") and d["tipo"] in ("gasto_caja", "caja_menor_manuscrito") and d["medio"] in ("", "Efectivo") and d.get("cuenta") == DOMICILIOS)
        pago_dom = max(cie.get("domicilios_pagados", 0) - en_vales, 0)
        for pago, cta, tot in ((pago_pro, PROPINAS, cie.get("propinas_total", 0)), (pago_dom, DOMICILIOS, cie.get("domicilios_pagados", 0))):
            if pago:
                if cta == PROPINAS: j_pro = len(datos)
                else: j_dom = len(datos)
                datos.append(dict(fecha=fecha, archivo="cierre de caja", tipo="cierre", numero="", tercero="Consumidor Final", detalle="Pago según cierre", valor=tot, medio="Efectivo",
                                  cuenta=cta, estado="ok", aviso="propinas pagadas según el cierre" if cta == PROPINAS else "domicilios pagados según el cierre (menos los vales)",
                                  propina=0, domicilio=0, bloque="cierre", id="", recibo="", motivo=""))
    # DEBT-1: las filas salen de DATOS OCR (una sola clasificación). Solo cuentan las filas «ok», como en los SUMIFS del Excel.
    ok = [(i, x) for i, x in enumerate(datos) if x["estado"] == "ok"]
    de = lambda bloque, **k: [(i, x) for i, x in ok if x["bloque"] == bloque and all(x[a] == b for a, b in k.items())]
    S = lambda col="valor", **c: ["sum", col, c]   # SUMIFS en DATOS OCR por fecha + estado «ok» + criterios (ADR-002)
    F = lambda *js: [["fila", j] for j in js if j is not None]
    suma = lambda xs, col="valor": sum(x[col] for _, x in xs)
    ids = lambda xs, col=None: [x["id"] for _, x in xs if col is None or x[col]]
    nums = lambda xs, col=None: [x["numero"] for _, x in xs if x["numero"] and (col is None or x[col])]

    def fila(cod, tercero, desc, deb=None, cre=None, reporta="", medio="", grupo="", docs=(), fx=None):
        """docs: ids de los papeles que originan la fila (N2). fx: de dónde sale el importe en el Excel (ADR-002), en el lado que se pasó:
        ["sum", col, {criterios}] · ["dato", i de datos] · ["fila", j de filas] · ["min"|"+"|"-", a, b, …]. Devuelve el índice de la fila."""
        filas.append(dict(fecha=fecha, codigo=cod, nombre=nombre(cod), tercero=tercero, descripcion=desc, debito=int(deb or 0), credito=int(cre or 0), reporta=reporta, medio=medio, grupo=grupo,
                          docs=[i for i in docs if i], fx=[("credito" if cre is not None else "debito"), fx] if fx else None))
        return len(filas) - 1

    # 1) recaudos del banco (de tu extracto). Si escribiste alguno, el extracto manda sobre lo que dicen las comandas pagadas al banco.
    ext = de("extracto"); total_b = suma(ext)
    jb = [fila(BANCO, "Consumidor Final", x["detalle"], deb=x["valor"], reporta=cfg["reporta_banco"], medio=x["medio"], grupo="venta", fx=["dato", i]) for i, x in ext]
    if total_b:
        cta = f"Recaudos pagados a la cta.{cfg['cuenta_recaudo']}" if cfg["cuenta_recaudo"] else "Recaudos pagados a la cuenta"
        # M-6: la propina y el domicilio de las comandas que cubre el extracto no son ingreso: van a 2815, con tope en lo que trae el extracto
        enx = [(i, x) for i, x in enumerate(datos) if x["estado"] == "en extracto" and x["bloque"] == "venta"]
        pro_x, dom_x = suma(enx, "propina"), suma(enx, "domicilio"); tot = ["+", *F(*jb)]; ex = dict(bloque="venta", estado="en extracto")
        if pro_x + dom_x > total_b:
            avisos.append("El extracto no alcanza para cubrir las propinas y domicilios de las comandas pagadas al banco")
            pro_x = min(pro_x, total_b); dom_x = min(dom_x, total_b - pro_x)
        jp = jd = None
        if pro_x: jp = fila(PROPINAS, "Consumidor Final", "Ordenes: " + abreviar_recibos(nums(enx, "propina")), cre=pro_x, reporta=cfg["reporta_banco"], grupo="venta",
                            fx=["min", S("propina", **ex), tot])
        if dom_x: jd = fila(DOMICILIOS, "Consumidor Final", "Ordenes: " + abreviar_recibos(nums(enx, "domicilio")), cre=dom_x, reporta=cfg["reporta_banco"], grupo="venta",
                            fx=["min", S("domicilio", **ex), ["-", tot, *F(jp)]])
        fila(RESTAURANTE, "Consumidor Final", cta, cre=total_b - pro_x - dom_x, reporta=cfg["reporta_banco"], grupo="venta", fx=["-", tot, *F(jp, jd)])
    for i, x in de("rappi"):   # Rappi te consigna lo que te debía: entra al banco y baja la cuenta por cobrar (no es una venta nueva)
        j = fila(BANCO, "Rappi", x["detalle"], deb=x["valor"], reporta=cfg["reporta_banco"], medio=x["medio"], grupo="venta", fx=["dato", i])
        fila(POR_COBRAR, "Rappi", x["detalle"], cre=x["valor"], reporta=cfg["reporta_banco"], grupo="venta", fx=["fila", j])

    # 2) ventas en efectivo (comandas): solo lo que entró en efectivo; la propina/domicilio pagados por tarjeta o app no pasan por la caja
    for d in docs:
        if d["tipo"] == "venta" and d["propina"] > d["efectivo"] + d["tarjeta"] + d["transf"] + d.get("credito", 0):
            avisos.append(f"Recibo {d['numero']}: la propina ({d['propina']:,}) es mayor que lo pagado".replace(",", "."))
    ve = de("venta", cuenta=EFECTIVO); efe, pro, dom = suma(ve), suma(ve, "propina"), suma(ve, "domicilio")
    if efe:
        if pro + dom > efe:   # el efectivo leído no alcanza (comanda mal leída): no se acredita más de lo que entró, para que el día cuadre
            avisos.append("El efectivo no alcanza para cubrir propinas y domicilios")
            pro = min(pro, efe); dom = min(dom, efe - pro)
        je = fila(EFECTIVO, "Consumidor Final", "Ordenes: " + abreviar_recibos(nums(ve, "valor")), deb=efe, reporta=cfg["reporta_efectivo"], medio="Efectivo", grupo="venta", docs=ids(ve, "valor"),
                  fx=S(bloque="venta", cuenta=EFECTIVO))
        jp = jd = None   # el tope al efectivo también va en la fórmula: MIN(propinas, efectivo) y MIN(domicilios, efectivo − propinas)
        if pro: jp = fila(PROPINAS, "Consumidor Final", "Ordenes: " + abreviar_recibos(nums(ve, "propina")), cre=pro, reporta=cfg["reporta_efectivo"], medio="Efectivo", grupo="venta",
                          fx=["min", S("propina", bloque="venta", cuenta=EFECTIVO), ["fila", je]])
        if dom: jd = fila(DOMICILIOS, "Consumidor Final", "Ordenes: " + abreviar_recibos(nums(ve, "domicilio")), cre=dom, reporta=cfg["reporta_efectivo"], medio="Efectivo", grupo="venta",
                          fx=["min", S("domicilio", bloque="venta", cuenta=EFECTIVO), ["-", *F(je, jp)]])
        fila(RESTAURANTE, "Consumidor Final", "Recaudos en efectivo", cre=efe - pro - dom, reporta=cfg["reporta_efectivo"], medio="Efectivo", grupo="venta", fx=["-", *F(je, jp, jd)])
    elif pro or dom:   # sin efectivo no hay filas de caja; la fila de DATOS OCR sí queda (valor 0) para corregir el efectivo allí
        avisos.append(f"El efectivo es 0 pero hay propina ({pro:,}) y domicilio ({dom:,}) en efectivo: no se contabilizan; corrige el efectivo".replace(",", "."))

    # 2b) ventas que no entraron en efectivo: tarjeta y transferencias/QR/Nequi/Bre-B → banco (salvo que hayas escrito el extracto:
    #     esas filas quedan «en extracto»), Rappi → ingresos por cobrar, crédito personal (fiado) → cuenta por cobrar al cliente.
    #     La propina y el domicilio pagados así ya vienen repartidos por medio en DATOS OCR.
    if total_b:
        enx = [(i, x) for i, x in enumerate(datos) if x["estado"] == "en extracto"]; al_banco = suma(enx)
        filas[jb[0]]["docs"] = list(dict.fromkeys(ids(enx)))
        if al_banco and al_banco != total_b:
            avisos.append(f"Recaudos del extracto ({total_b:,}) ≠ comandas pagadas con tarjeta/transferencia ({al_banco:,}); se usó el extracto".replace(",", "."))
    partes = [(i, x) for i, x in de("venta") if x["cuenta"] not in (EFECTIVO, cfg["puente_ingreso"])]
    grupos = defaultdict(list)
    for p in partes: grupos[(p[1]["cuenta"], p[1]["tercero"], p[1]["medio"])].append(p)
    rep = cfg["reporta_banco"]; jg = []
    for (cod, ter, medio), ps in grupos.items():
        ords = "Ordenes: " + abreviar_recibos(nums(ps))
        desc = RECAUDO_DESC.get(medio, f"Recaudos por {medio}") + (" · " + ords if ords != "Ordenes: " else "")
        jg.append(fila(cod, ter, desc, deb=suma(ps), reporta=rep, medio=medio, grupo="venta", docs=ids(ps), fx=S(bloque="venta", cuenta=cod, tercero=ter, medio=medio)))
    if partes:
        pro_e, dom_e = suma(partes, "propina"), suma(partes, "domicilio")
        jp = jd = None; no_ef = dict(bloque="venta", cuenta="<>" + EFECTIVO)
        if pro_e: jp = fila(PROPINAS, "Consumidor Final", "Ordenes: " + abreviar_recibos(nums(partes, "propina")), cre=pro_e, reporta=rep, grupo="venta", fx=S("propina", **no_ef))
        if dom_e: jd = fila(DOMICILIOS, "Consumidor Final", "Ordenes: " + abreviar_recibos(nums(partes, "domicilio")), cre=dom_e, reporta=rep, grupo="venta", fx=S("domicilio", **no_ef))
        fila(RESTAURANTE, "Consumidor Final", "Recaudos con tarjeta, transferencias, apps y crédito", cre=suma(partes) - pro_e - dom_e, reporta=rep, grupo="venta",
             fx=["-", ["+", *F(*jg)], *F(jp, jd)])
    sin_medio = de("venta", cuenta=cfg["puente_ingreso"])
    for _, x in sin_medio:   # no se leyó con qué se pagó: entra a la cuenta puente, no se descarta (R10)
        avisos.append(f"Recibo {x['numero'] or 's/n'}: no se leyó con qué se pagó ({x['valor']:,}); quedó en la cuenta puente {cfg['puente_ingreso']}, corrige el medio".replace(",", "."))
    if sin_medio:
        ords = "Ordenes: " + abreviar_recibos(nums(sin_medio))
        j = fila(cfg["puente_ingreso"], "Consumidor Final", "Venta sin medio de pago · " + ords, deb=suma(sin_medio), reporta=cfg["reporta_banco"], grupo="venta", docs=ids(sin_medio),
                 fx=S(bloque="venta", cuenta=cfg["puente_ingreso"]))
        fila(RESTAURANTE, "Consumidor Final", "Venta sin medio de pago · " + ords, cre=suma(sin_medio), reporta=cfg["reporta_banco"], grupo="venta", docs=ids(sin_medio), fx=["fila", j])
    if ajuste:
        j = fila(cfg["puente_ingreso"], "Consumidor Final", "Ajuste al cierre (cierre > papeles)", deb=ajuste, reporta=cfg["reporta_banco"], grupo="venta", fx=["dato", j_aj])
        fila(RESTAURANTE, "Consumidor Final", "Ajuste al cierre (cierre > papeles)", cre=ajuste, reporta=cfg["reporta_banco"], grupo="venta", fx=["fila", j])
        avisos.append(f"Ajuste al cierre: el cierre del POS vendió {ajuste:,} más que tus comandas; quedó en la cuenta puente {cfg['puente_ingreso']} (falta una comanda o se leyó mal)".replace(",", "."))
    elif cie.get("total_vendido") and fecha_cierre and sum(d["consumo"] for d in todos if d["tipo"] == "venta" and d.get("contar")) - cie["total_vendido"] > 1:
        sobra = sum(d["consumo"] for d in todos if d["tipo"] == "venta" and d.get("contar")) - cie["total_vendido"]
        avisos.append(f"Tus comandas suman {sobra:,} más que el cierre del POS: no se ajustó nada, revisa si hay una comanda repetida o mal leída".replace(",", "."))

    # 3) caja menor: un renglón por cuenta + un crédito a Efectivo (sin cuenta = puente: una sola fila con los que ya estaban ahí, FIX-3)
    cm = de("caja"); por_cuenta = defaultdict(list)
    for p in cm: por_cuenta[p[1]["cuenta"]].append(p)
    sin_cuenta = [x for _, x in cm if x["aviso"] == FALTA_CUENTA]
    if sin_cuenta: avisos.append(f"{len(sin_cuenta)} gasto(s) de caja sin cuenta: " + ", ".join(x["numero"] or "s/n" for x in sin_cuenta) + f"; quedaron en la cuenta puente {cfg['puente_gasto']}")
    jc = []
    for cod, ps in sorted(por_cuenta.items(), key=lambda kv: (kv[0] == cfg["puente_gasto"], kv[0])):
        jc.append(fila(cod, "Cuantías menores", "Recibos: " + rangos(nums(ps)), deb=suma(ps), reporta=cfg["reporta_efectivo"], medio="Efectivo", grupo="gasto",
                       docs=ids(ps), fx=S(bloque="caja", cuenta=cod)))
    if cm:
        fila(EFECTIVO, "Cuantías menores", "Recibos: " + rangos(nums(cm)), cre=suma(cm), reporta=cfg["reporta_efectivo"], medio="Efectivo", grupo="gasto", fx=["+", *F(*jc)])

    # 3b) R2: pago de propinas y domicilios según el cierre → débito a 2815 contra Efectivo
    if pago_pro or pago_dom:
        jr = []
        if pago_pro:
            jr.append(fila(PROPINAS, "Consumidor Final", "Pago de propinas según cierre", deb=pago_pro, reporta=cfg["reporta_efectivo"], medio="Efectivo", grupo="gasto", fx=["dato", j_pro]))
        if pago_dom:
            en_v = S(bloque="caja", cuenta=DOMICILIOS)   # domicilios = dato − MIN(dato, vales): nunca negativo, sin repetir lo que ya pagaron los vales
            jr.append(fila(DOMICILIOS, "Consumidor Final", "Pago de domicilios según cierre", deb=pago_dom, reporta=cfg["reporta_efectivo"], medio="Efectivo", grupo="gasto",
                           fx=["-", ["dato", j_dom], ["min", ["dato", j_dom], en_v]]))
        fila(EFECTIVO, "Consumidor Final", "Pago de propinas y domicilios según cierre", cre=pago_pro + pago_dom, reporta=cfg["reporta_efectivo"], medio="Efectivo", grupo="gasto", fx=["+", *F(*jr)])

    # 4) facturas y gastos pagados por banco o en efectivo, uno por uno (si no se leyó el valor, no se inventa un asiento: queda en pendientes)
    for i, x in enumerate(datos):
        if x["bloque"] != "factura": continue
        ref = x["numero"] or x["tercero"] or "s/n"
        if x["estado"] == "pendiente":
            pendientes.append(dict(id=x["id"], tipo=x["tipo"], numero=x["numero"], tercero=x["tercero"], valor=0, motivo="sin valor leído"))
            avisos.append(f"Factura {ref}: sin valor leído, quedó en pendientes (corrige el valor o desmárcala)"); continue
        if x["medio"] in ("Tarjeta", "Mixto"): avisos.append(f"Factura {ref}: pagada con tarjeta; se registró contra Bancos, revisa el medio")
        if x["aviso"] == FALTA_CUENTA: avisos.append(f"Factura {ref}: falta la cuenta; quedó en la cuenta puente {cfg['puente_gasto']}")
        ef = x["medio"] == "Efectivo"; rep = cfg["reporta_efectivo"] if ef else cfg["reporta_banco"]
        desc = x["detalle"] or "Compra"; ter = x["tercero"] or "Proveedor"
        j = fila(x["cuenta"], ter, desc, deb=x["valor"], reporta=rep, medio=x["medio"], grupo="gasto", docs=[x["id"]], fx=["dato", i])
        fila(EFECTIVO if ef else BANCO, ter, desc, cre=x["valor"], reporta=rep, medio=x["medio"], grupo="gasto", docs=[x["id"]], fx=["fila", j])
    for d in docs:
        if d["tipo"] in ("venta", "gasto_caja", "factura") and d.get("avisos") and estado_de(d) != "revisado":
            avisos += [f"{d['tipo'].replace('_', ' ').capitalize()} {d['numero'] or ''}: {a}".replace("  ", " ") for a in d["avisos"]]
        if d["tipo"] == "venta" and estado_de(d) == "dudoso":   # T12 (R7): el motivo de la validación, si no es ya un aviso
            avisos += [f"Venta {d['numero'] or ''} dudosa: {m}".replace("  ", " ") for m in d.get("motivos") or [] if m not in (d.get("avisos") or [])]
    cruces, faltan = cruzar([d for d in todos if d["tipo"] != "cierre"], cie)
    if faltan: avisos.insert(0, "Faltan comandas del cierre: " + ", ".join(map(str, faltan)))
    if faltan: avisos.append("Falta la comanda " + ", ".join(map(str, faltan)) + " (está en el rango del cierre)")
    for n, k in sorted(numeros_repetidos(docs).items()):
        avisos.append(f"Comanda {n}: número repetido en {k} recibos distintos (no coinciden hora, mesa y valores): revisa el número en el papel")
    raros = fuera_de_secuencia(docs, int(cfg["salto_comanda"]))
    if raros:
        ns = sorted({int(d["numero"]) for d in docs if d["tipo"] == "venta" and str(d.get("numero", "")).isdigit()} - set(raros))
        avisos.append(f"Comanda{'s' if len(raros) > 1 else ''} {', '.join(map(str, raros))}: no sigue{'n' if len(raros) > 1 else ''} la secuencia del día ({ns[0]}–{ns[-1]}); ¿es de otro día (fecha reimpresa) o se leyó mal el número?")
    if any(not x["ok"] for x in cruces): avisos.append(f"El cierre del POS no coincide con tus papeles en {sum(not x['ok'] for x in cruces)} concepto(s): ¿falta alguna comanda o se leyó mal?")
    deb, cre = sum(f["debito"] for f in filas), sum(f["credito"] for f in filas)
    if deb != cre: avisos.insert(0, f"El día no cuadra: débito {deb:,} · crédito {cre:,} (diferencia {deb - cre:,})".replace(",", "."))
    return dict(filas=filas, datos=datos,debito=deb, credito=cre, diferencia=deb - cre, avisos=avisos, pendientes=pendientes, documentos=todos, cierre=cie, cruces=cruces, faltan=faltan)
