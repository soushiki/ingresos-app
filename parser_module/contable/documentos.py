"""Texto plano (módulo 1) → documentos tipados: venta, gasto de caja, recibo de caja menor, factura de proveedor."""
from __future__ import annotations
import datetime, json, re, uuid
from pathlib import Path
from ..numeros import _MES, _MN, extraer_fecha, norm

MARCA = "=== DOCUMENTO ==="
_MONTO = re.compile(r"\$?\s*(\d{1,3}(?:[.,]\d{3})+|\d+)(?:[.,]\d{1,2})?(?!\d)")
# Medio de pago: el crudo que se lee (Nequi, Daviplata…) → uno de los 8 canónicos (mapa único en normalizacion.json/medio_canonico).
MEDIOS_CANON = ("Efectivo", "Transferencia", "Tarjeta", "QR", "Bre-B", "PSE", "App", "Crédito personal")
_MAPA_MEDIO = json.loads((Path(__file__).parent / "normalizacion.json").read_text(encoding="utf8"))["medio_canonico"]
# crudo legible por clave (para medio_detalle / descripción del asiento); el orden de lectura es el del mapa, «credito personal» antes que «credito»
MEDIOS = [(k, {"nequi": "Nequi", "daviplata": "Daviplata", "datafono": "Datáfono", "rappi": "Rappi"}.get(k, v)) for k, v in _MAPA_MEDIO.items()]


def medio_canonico(texto) -> tuple:
    """(medio, aviso): uno de MEDIOS_CANON, o ("", aviso) si no se reconoce; «(sin medio)»/vacío → ("", "") y nunca se inventa."""
    n = norm(texto or "").strip()
    if not n or n in ("(sin medio)", "sin medio"): return "", ""
    for k, v in sorted(_MAPA_MEDIO.items(), key=lambda kv: -len(kv[0])):
        if re.search(r"(?<![a-z])" + re.escape(k), n): return v, ""
    return "", f"Medio de pago no reconocido: «{texto}»"
# «PAGA CON …» de una comanda: tarjeta (datáfono), crédito personal (fiado) o electrónico (transferencia, app, QR…). El orden importa:
# «CRED.PERSONA» no es tarjeta de crédito.
PAGO_FIADO = r"paga con cred\w*\W*person"
PAGO_TARJETA = r"paga con (?!cred\w*\W*person)(?:credito|cred\b|debito|tarjeta|visa|master\w*|amex|american|diners|datafono)"
PAGO_ELEC = r"paga con (?:transf\w*|consign\w*|qr|nequi|daviplata|app|bre\W?b|llave|pse|rappi|didi|ifood|bancolombia)"


def monto(s) -> int:
    m = _MONTO.search(s or "")
    return int(re.sub(r"\D", "", m.group(1))) if m else 0


def montos(s) -> list:
    return [int(re.sub(r"\D", "", m.group(1))) for m in _MONTO.finditer(s or "")]


def separar(texto: str) -> list:
    """Una foto puede traer varios papeles: el OCR los separa con «=== DOCUMENTO ===»."""
    partes = [p.strip() for p in re.split(r"^\s*=+\s*DOCUMENTO\s*=+\s*$", texto or "", flags=re.M | re.I) if p.strip()]
    # M-9: con o sin marcas, un bloque con dos membretes son dos recibos pegados por el OCR → se parte por membrete
    return [q.strip() for p in partes for q in (re.split(r"(?=^\s*SU RESTAURANTE\s*$)", p, flags=re.M | re.I)
                                                if len(re.findall(r"^\s*SU RESTAURANTE\s*$", p, flags=re.M | re.I)) >= 2 else [p]) if len(q.strip()) > 15]


def _lineas(t): return [l.strip() for l in t.splitlines() if l.strip()]


def _valor_linea(lineas, patron, excluir=None, ultimo=False):
    for l in lineas:
        n = norm(l)
        if re.search(patron, n) and not (excluir and re.search(excluir, n)):
            resto = re.split(patron, n, maxsplit=1)[-1]
            v = montos(resto)
            if v: return v[-1] if ultimo else v[0]
    return 0


CATEGORIA = {"cierre": "cierre", "venta": "comandas", "gasto_caja": "gastos", "caja_menor_manuscrito": "gastos", "factura": "gastos"}
FAMILIA = {"cierre": ("cierre",), "comandas": ("venta", "rappi"), "gastos": ("gasto_caja", "caja_menor_manuscrito", "factura")}
_RAPPI_ID = r"\bid\s*:?\s*\d{8,}"


def detectar_tipo(texto: str) -> str:
    n = norm(texto)
    if "cierre de caja" in n and ("resumido" in n or "valores $" in n or "base de caja" in n or "efectivo en caja" in n or "ventas por" in n): return "cierre"
    if "recibo de caja menor" in n and "gasto de caja" not in n: return "caja_menor_manuscrito"
    if "gasto de caja" in n: return "gasto_caja"
    if "rappi" in n and ("sugerido a facturar" in n or (re.search(_RAPPI_ID, n) and ("plataforma" in n or "fecha orden" in n))): return "rappi"
    if "total a pagar" in n or re.search(r"recibo\s*#", n) or "paga con efectivo" in n or "mesero" in n: return "venta"
    if "factura" in n or "subtotal" in n or re.search(r"\btotal\b", n): return "factura"
    return "otro"


def _medio_crudo(texto: str, primeras: int = 3, solo_primeras=False) -> str:
    ls = _lineas(texto)
    zonas = [" ".join(ls[:primeras])] + ([] if solo_primeras else [l for l in ls if re.search(r"m[eé]todo de pago|medio pago|medio de pago", l, re.I)])
    for z in zonas:
        n = norm(z)
        for k, v in sorted(_MAPA_MEDIO.items(), key=lambda kv: -len(kv[0])):
            if re.search(r"(?<![a-z])" + re.escape(k), n): return dict(MEDIOS)[k]
    return ""


def _medio(texto: str, primeras: int = 3, solo_primeras=False) -> str:
    return medio_canonico(_medio_crudo(texto, primeras, solo_primeras))[0]


def _base(tipo, texto):
    return dict(id=uuid.uuid4().hex[:8], tipo=tipo, numero="", fecha="", tercero="", detalle="", valor=0, consumo=0, propina=0,
                domicilio=0, efectivo=0, tarjeta=0, transf=0, credito=0, medio_transf="", cliente="", descuento=0, cortesia=0, medio="", medio_detalle="", cuenta="", conf=0.0, motivo="", contar=True, dup_de="", avisos=[], texto=texto)


def _lineas_que(L, patron):
    return [l for l in L if re.search(patron, norm(l))]


_ITEM = re.compile(r"^\W*(?P<nombre>[^|]*?[^\W\d_][^|]*?)\s*\|\s*(?P<cant>\d{1,3})\s*\|\s*\$?\s*(?P<valor>\d[\d.,]*)\s*\|?\s*$")


def _hora(n: str) -> str:
    """«Fecha de Venta: 16/09/2026 8:01:37 p. m.» → «20:01» (24 h); vacío si no se lee."""
    m = re.search(r"fecha de venta\W[^\n]*?\b(\d{1,2}):(\d{2})(?::\d{2})?\s*(?:(a|p)\W*m\b)?", n)
    if not m: return ""
    h, mi = int(m.group(1)), int(m.group(2))
    if h > 23 or mi > 59: return ""
    if m.group(3) == "p" and h < 12: h += 12
    if m.group(3) == "a" and h == 12: h = 0
    return f"{h:02d}:{mi:02d}"


def _items(L) -> list:
    """Filas «| nombre | cant | valor |» (valor = total de la fila, como lo imprime el POS). Las de encabezado no entran."""
    out = []
    for l in L:
        m = _ITEM.match(l)
        if m and not re.search(r"descripcion|^\W*(?:sub)?total|\bcant\b", norm(m.group("nombre"))):
            out.append(dict(cant=int(m.group("cant")), nombre=m.group("nombre").strip(" |"), valor=monto(m.group("valor"))))
    return out


def parse_venta(texto):
    """Comanda / recibo de venta del POS. Todo se lee por etiqueta («TOTAL CONSUMO», «PROPINA», «PAGADO», «PAGA CON …»)."""
    d = _base("venta", texto); L = _lineas(texto); n = norm(texto)
    m = re.search(r"recibo\s*#?\s*:?\s*(\d{3,})", n); d["numero"] = m.group(1) if m else ""
    d["fecha"] = extraer_fecha(n)[0] or ""
    total_consumo = _valor_linea(L, r"total consumo", excluir=r"subtotal"); subtotal = _valor_linea(L, r"subtotal consumo"); total_pagar = _valor_linea(L, r"total a pagar")
    d["descuento"] = _valor_linea(L, r"^\W*descuento")
    d["domicilio"] = _valor_linea([l for l in L if not re.search(r"servicio|domiciliario", norm(l))], r"^\W*domicilio\b")
    d["propina"] = _valor_linea(L, r"^\W*propina")
    pagado = _valor_linea(L, r"^\W*pagado"); cambio = _valor_linea(L, r"^\W*cambio")
    for k in ("descuento", "domicilio", "propina"):
        if d[k] < 100: d[k] = 0                  # un «$» vacío que el OCR lee como «3» no es una propina de 3 pesos
    if cambio < 100: cambio = 0
    consumo = total_consumo or subtotal or max(0, total_pagar - d["domicilio"])
    cortesia = bool(re.search(r"total a pagar\W*cortesia", n))
    d["consumo"] = max(0, consumo - d["descuento"])
    if cortesia: d["cortesia"] = d["descuento"] or consumo; d["consumo"] = 0
    l_fiado, l_card, l_elec = _lineas_que(L, PAGO_FIADO), _lineas_que(L, PAGO_TARJETA), _lineas_que(L, PAGO_ELEC)
    d["credito"] = sum(_valor_linea([l], PAGO_FIADO) for l in l_fiado)
    d["tarjeta"] = sum(_valor_linea([l], PAGO_TARJETA) for l in l_card)
    d["transf"] = sum(_valor_linea([l], PAGO_ELEC) for l in l_elec)
    if l_elec: d["medio_transf"] = _medio_crudo(l_elec[0], 1, True) or "Transferencia"
    efe_lineas = [l for l in L if re.match(r"^\W*(?:paga con )?efectivo\b", norm(l))]
    if efe_lineas:
        efe = _valor_linea(efe_lineas, r"efectivo") or (pagado - d["tarjeta"] - d["transf"] - d["credito"])    # «EFECTIVO» sin cifra = lo que dice PAGADO
        d["efectivo"] = max(0, efe - cambio)
    # Un solo medio que no es efectivo (no hay cambio): si su cifra no se leyó o salió cortada («$43,0»), vale lo PAGADO
    # o, si tampoco se leyó, consumo + domicilio + propina.
    unico = [k for k, ls in (("credito", l_fiado), ("tarjeta", l_card), ("transf", l_elec)) if ls]
    if len(unico) == 1 and not efe_lineas:
        k = unico[0]; total = pagado or (d["consumo"] + d["domicilio"] + d["propina"] if not cortesia else 0)
        if total and d[k] != total and (pagado or d[k] < total * 0.5): d[k] = total
    d["items"], d["subtotal"], d["pagado"], d["cambio"], d["hora"] = _items(L), subtotal, pagado, cambio, _hora(n)
    cli = re.search(r"^\s*cliente\s*:?\s*(.+)$", texto, flags=re.M | re.I)
    if cli and not re.search(r"consumidor final", norm(cli.group(1))): d["cliente"] = cli.group(1).strip().title()
    mm = re.search(r"mesa\s*:?\s*([a-z0-9]+)", n); mesero = re.search(r"mesero\s*:?\s*([a-z]+)", n)
    d["detalle"] = " · ".join(x for x in (f"Mesa {mm.group(1).upper()}" if mm else "", f"Mesero {mesero.group(1).capitalize()}" if mesero else "",
                                           f"CORTESÍA {d['cortesia']:,}".replace(",", ".") if cortesia else "", "con domicilio" if d["domicilio"] else "") if x)
    d["tercero"] = "Consumidor Final"
    usados = [m for m, v in (("Efectivo", d["efectivo"]), ("Tarjeta", d["tarjeta"]), (d["medio_transf"] or "Transferencia", d["transf"]), ("Crédito personal", d["credito"])) if v]
    d["medio"] = "Mixto" if len(usados) > 1 else (usados[0] if usados else "")
    if not d["numero"]: d["avisos"].append("No se leyó el número de recibo")
    if not d["consumo"] and not cortesia: d["avisos"].append("No se leyó el total del consumo")
    pagos, esperado = d["efectivo"] + d["tarjeta"] + d["transf"] + d["credito"], d["consumo"] + d["domicilio"] + d["propina"]
    if not cortesia and d["consumo"] and pagos != esperado:
        d["avisos"].append(f"Los pagos ({pagos:,}) no suman consumo + domicilio + propina ({esperado:,})".replace(",", "."))
    return d


def parse_rappi(texto):
    """Papel que imprime Rappi (ID largo + «Total sugerido a facturar»): una venta cobrada por la app, que Rappi paga después (13452501).
    Nunca se inventa el valor: sin «Total sugerido» se usa «Subtotal» con aviso; sin ninguno, 0 + aviso."""
    d = _base("venta", texto); L = _lineas(texto); n = norm(texto)
    m = re.search(_RAPPI_ID.replace(r"\d{8,}", r"(\d{8,})"), n); d["numero"] = m.group(1) if m else ""
    d["fecha"] = extraer_fecha(n)[0] or ""   # la «Fecha orden» impresa no manda: la carpeta la reemplaza (aplicar_fecha_carpeta)
    v = _valor_linea(L, r"sugerido a facturar")
    if not v:
        v = _valor_linea(L, r"^\W*subtotal")
        d["avisos"].append("Se usó el subtotal de Rappi (no se leyó el total sugerido a facturar)" if v else "No se leyó el total de Rappi")
    if not d["numero"]: d["avisos"].append("No se leyó el ID de Rappi")
    d["rappi"] = True; d["consumo"] = d["valor"] = d["transf"] = v
    d["medio"] = d["medio_transf"] = "Rappi"; d["tercero"] = "Rappi"; d["detalle"] = "Pedido Rappi"
    d["items"] = _items(L)
    return d


def parse_gasto(texto):
    d = _base("gasto_caja", texto); L = _lineas(texto); n = norm(texto)
    m = re.search(r"consecutivo\s*:?\s*(\d+)", n); d["numero"] = m.group(1) if m else ""
    d["fecha"] = extraer_fecha(n)[0] or ""; d["valor"] = _valor_linea(L, r"^\W*valor\W*")
    i = next((k for k, l in enumerate(L) if re.search(r"descripci", norm(l))), None)
    if i is not None:
        resto = re.split(r"descripci[oó]n\s*:?", L[i], flags=re.I)[-1].strip()
        cola = []
        for l in L[i + 1:]:
            if re.search(r"^\W*(firma|c\.?c\.?)", norm(l)): break
            cola.append(l)
        d["detalle"] = " ".join(x for x in [resto] + cola if x).strip()
    if not d["detalle"]:
        j = next((k for k, l in enumerate(L) if re.search(r"fecha de entrega", norm(l))), None)
        for l in (L[j + 1:j + 3] if j is not None else []):
            limpio = re.sub(r"[^A-Za-zÁÉÍÓÚÑáéíóúñ ]+.*$", "", l).strip()
            if len(limpio.split()) >= 2 and not re.search(r"firma|codigo|aprobado|recibo", norm(limpio)): d["detalle"] = limpio; break
    r = re.search(r"responsable\s*:?\s*([a-z ]+)", n); d["tercero"] = "Cuantías menores"
    d["medio_detalle"] = _medio_crudo(texto, 0) if re.search(r"medio pago\s*:\s*\S", n) else ""
    d["medio"] = (_medio(texto, 0) or "Efectivo") if re.search(r"medio pago\s*:\s*\S", n) else "Efectivo"
    if not d["valor"]: d["avisos"].append("No se leyó el valor")
    if not d["numero"]: d["avisos"].append("No se leyó el consecutivo")
    return d


def parse_manuscrito(texto):
    d = _base("caja_menor_manuscrito", texto); L = _lineas(texto)
    d["valor"] = _valor_linea(L, r"valor\W*") or next((v for l in L for v in montos(l) if v >= 100), 0)
    d["detalle"] = " ".join(l for l in L if not re.search(r"recibo de caja|valor|c\.?c\.? no|^\W*firma", norm(l)) and not _MONTO.fullmatch(l.strip("$ ")))[:120]
    d["tercero"] = "Cuantías menores"; d["medio"] = "Efectivo"
    d["avisos"].append("Recibo manuscrito: se descarta si coincide con un gasto de caja impreso")
    return d


_NO_NOMBRE = re.compile(r"cliente|vendedor|direcci|ciudad|factura|nit|\bcc\b|cra\b|calle|carrera|tel|forma de|m[eé]todo|fecha|consumidor|subtotal|total|vencimiento|documento|r[eé]gimen|www|@|local|bolivar|cartagena", re.I)


def _total_factura(L) -> int:
    """El total de una factura: «TOTAL NETO», «TOTAL A PAGAR» o «TOTAL: $…»; si no, lo pagado con visa/efectivo/transferencia; si no, el subtotal."""
    for pat in (r"total neto", r"^\W*total a pagar", r"^\W*total\W*[:$\d>]", r"^\W*total factura", r"^\W*(?:visa|mastercard|efectivo|transferencia|tarjeta)\b.*\$", r"subtotal"):
        for l in L:
            nl = norm(l)
            if re.search(pat, nl) and not re.match(r"^\W*total (de|recibido|items|descuento|l)", nl):
                v = montos(re.split(pat, nl, maxsplit=1)[-1] if pat != r"^\W*total\W*[:$\d>]" else l.split(":", 1)[-1])
                if v: return max(v) if pat.startswith("^\\W*(?:visa") else v[0]
    return 0


def parse_factura(texto):
    d = _base("factura", texto); L = _lineas(texto); n = norm(texto)
    m = re.search(r"\b([A-Za-z]{1,6}\d{3,})\b", texto); d["numero"] = m.group(1) if m else ""
    d["fecha"] = extraer_fecha(n)[0] or ""
    d["valor"] = _total_factura(L)
    nombres = [l for l in L[:8] if len(l.split()) >= 2 and not _NO_NOMBRE.search(l) and sum(c.isalpha() or c == " " for c in l) / len(l) > 0.85]
    d["tercero"] = nombres[0].title() if nombres else ""
    rs = next((i for i, l in enumerate(L) if re.search(r"raz[oó]n social", l, re.I)), None)   # factura electrónica: el emisor
    if rs is not None:
        nom = re.split(r"raz[oó]n social\s*:?", L[rs], flags=re.I)[-1].strip()
        if rs + 1 < len(L) and re.fullmatch(r"(?:S\.?\s?A\.?\s?S\.?|S\.?\s?A\.?|LTDA\.?)", L[rs + 1].strip(), re.I): nom += " " + L[rs + 1].strip()
        if nom: d["tercero"] = nom.title()
    f = next((l for l in L if re.search(r"factura", norm(l))), "")
    d["detalle"] = re.sub(r"\s+", " ", f).strip()
    d["medio_detalle"] = _medio_crudo(texto, 3, True) or _medio_crudo(texto, 0)
    d["medio"] = medio_canonico(d["medio_detalle"])[0]
    if not d["valor"]: d["avisos"].append("No se leyó el total")
    if not d["tercero"]: d["avisos"].append("No se leyó el proveedor")
    if not d["medio"]: d["avisos"].append("No se leyó el medio de pago")
    return d


_NO_ITEM = re.compile(r"descripci|desciprci|total|\bcant\b|vr\.? ?unit|subtotal|iva|domicilio|propina|dcto|descuento|efectivo|cambio|nit|cufe|fecha|telefono")
_NUM = r"\$?\s*\d[\d.,]*"
_TOPE_ITEM = 5_000_000   # un «ítem» mayor es un NIT, CUFE o resolución, no un valor
_MIN_ITEM = 100          # un «Reci: | 1 | 1» no es un ítem


def _item(nombre, valor, cant=1):
    return dict(nombre=nombre, cant=cant, valor=valor, cuenta="", conf=0.0, capa="", motivo="", manual="")


def _items_texto(texto: str) -> list:
    """Ítems de una factura: filas «| nombre | … | valor |» (valor = último número) o líneas «nombre … valor». Spike T1: los de tabla mandan."""
    tabla, plano = [], []
    for l in (texto or "").splitlines():
        if _NO_ITEM.search(norm(l)): continue
        if l.count("|") >= 2:
            celdas = [c.strip() for c in l.split("|") if c.strip()]
            nums = [c for c in celdas if re.fullmatch(_NUM, c)]
            nom = next((c for c in celdas if re.search(r"[^\W\d_]{3,}", c)), "")
            if nom and nums and _MIN_ITEM <= monto(nums[-1]) < _TOPE_ITEM: tabla.append(_item(nom, monto(nums[-1])))
        elif "|" not in l:
            m = re.match(rf"^\W*(?:\d{{1,3}}\s+)?(?P<n>[^\W\d_][^\d$]{{2,}}?)\s+(?P<v>{_NUM})\s*$", l)
            if m and _MIN_ITEM <= monto(m.group("v")) < _TOPE_ITEM: plano.append(_item(m.group("n").strip(), monto(m.group("v"))))
    return tabla or plano


def items_de(doc: dict) -> list:
    """Ítems del papel (R2, 03-design C4), sin tocarlo: [{nombre, cant, valor, cuenta, conf, capa, motivo, manual}].
    · ya trae items[].cuenta → tal cual (idempotente);
    · factura cuyos ítems del texto suman el total ±1 % (T1: solo esas se reparten) → esos ítems;
    · si no → un ítem único (detalle + proveedor) por el valor del papel. Migración al leer: papel viejo → su `cuenta` y manual = `cuenta_manual`."""
    previos = doc.get("items") or []
    if previos and all(isinstance(i, dict) and "cuenta" in i for i in previos): return previos
    total = doc.get("valor") or doc.get("consumo") or 0
    if doc.get("tipo") == "factura" and total:
        its = _items_texto(doc.get("texto", ""))
        if its and abs(sum(i["valor"] for i in its) - total) <= 0.01 * total: return its
    nombre = " ".join(x for x in (doc.get("detalle") or "", doc.get("tercero") or "") if x).strip()
    uno = _item(nombre, total)
    cm = doc.get("cuenta_manual")      # la app guarda un booleano (contable.html); papeles muy viejos, el código
    uno["cuenta"] = doc.get("cuenta") or ""
    uno["manual"] = (uno["cuenta"] if cm is True else cm if isinstance(cm, str) else "")
    return [uno]


def _primero(L, patron, **kw):
    return _valor_linea(L, patron, **kw)


def parse_cierre(texto):
    """«Cierre de caja resumido» del POS (puede venir en varias hojas: las cifras se juntan). Lee por etiqueta, con tolerancia al OCR."""
    d = _base("cierre", texto); L = _lineas(texto); n = norm(texto)
    # la fecha del cierre es la de «Cierre del:» o «Ventas por horas»; las demás fechas de la hoja son de platos cancelados de otros días
    d["fecha"] = next((f for l in L if re.search(r"cierre del|ventas por horas", norm(l)) and (f := extraer_fecha(norm(l))[0])), "")
    d["contar"] = False; d["detalle"] = "Cierre de caja resumido"; d["tercero"] = "POS"
    T = r"tar\w*jetas"
    dat = {
        "total_vendido": _primero(L, r"total vendido en el dia"), "descuentos": _primero(L, r"total descuentos"),
        "tarjetas_sin_prop": _primero(L, rf"total {T} sin prop"), "tarjetas_con_prop": _primero(L, rf"total {T} con prop"),
        "transferencias": _primero(L, r"total ingresos con app", excluir=r"\befe"), "propinas_total": _primero(L, r"^\W*total propinas\b", excluir=r"con app"),
        "propinas_efectivo": _primero(L, r"propinas en efectivo"), "propinas_app": _primero(L, r"propinas por transferencias"),
        "domicilios_vendidos": _primero(L, r"total vendido en domicilios"), "domicilios_num": _primero(L, r"total numero de domicilios"),
        "domicilios_pagados": _primero(L, r"total pagado en domicilios"), "base_caja": _primero(L, r"base de c\w*"),
        "venta_efectivo": _primero(L, r"total venta en efectivo"), "gastos_caja": _primero(L, r"^\W*total gastos"),
        "efectivo_esperado": _primero(L, r"total efectivo en caja"), "efectivo_contado": _primero(L, r"efectivo regis"),
        "factura_inicial": _primero(L, r"factura inicial"), "factura_final": _primero(L, r"factura final"), "transacciones": _primero(L, r"^\W*transacciones"),
    }
    def _detalle(ini, fin):
        """Suma de un bloque «DETALLADO …» (una línea por medio: «1 VISA 125950»); la hoja final del cierre trae solo estos bloques."""
        i = next((k for k, l in enumerate(L) if re.search(ini, norm(l))), None); tot = 0
        if i is None: return 0
        for l in L[i + 1:]:
            if re.search(fin, norm(l)) or "@" in l: break
            v = montos(l)
            if v and v[-1] >= 100: tot += v[-1]
        return tot
    if not dat["tarjetas_con_prop"]: dat["tarjetas_con_prop"] = _detalle(r"detallado tar\w*jetas", r"detallado|gastos|creditos|denominacion")
    if not dat["transferencias"]: dat["transferencias"] = _detalle(r"detallado pagos con app", r"detallado|gastos|creditos|denominacion")
    sob, fal = _primero(L, r"^\W*sobrante"), _primero(L, r"^\W*faltante")
    dat["faltante_impreso"] = sob if sob else -fal if fal else 0
    ini = next((i for i, l in enumerate(L) if re.search(r"gastos detallados", norm(l))), None)
    gd = []
    if ini is not None:
        for l in L[ini + 1:]:
            if re.search(r"denominacion|efectivo regis|creditos detallados|detallado", norm(l)): break
            v = montos(l)
            if v: gd.append([re.sub(r"[\s$\d.,]+$", "", l).strip(), v[-1]])
    d["datos"] = {k: int(v) for k, v in dat.items()}; d["gastos_detalle"] = gd
    d["leidos"] = sum(1 for v in d["datos"].values() if v)
    if d["leidos"] < 3: d["avisos"].append("Se reconocieron pocas cifras de esta hoja del cierre (puede ser una hoja intermedia)")
    return d


PARSERS = {"cierre": parse_cierre, "venta": parse_venta, "rappi": parse_rappi, "gasto_caja": parse_gasto, "caja_menor_manuscrito": parse_manuscrito, "factura": parse_factura}

# M-10: cada escaneo trae papeles de una sola fecha y su carpeta la dice (manda sobre la impresa). «20 SEPT 26» trae la fecha completa;
# una carpeta de solo el día («SEPTIEMBRE/6/») toma el mes de la carpeta de arriba y el año más común de las fechas impresas (usuario,
# 2026-10-18). El nombre del archivo («cierre20261002_…», «10-09.jpg») trae la fecha del escaneo, no la del papel: no cuenta.
_CARPETA = re.compile(rf"(\d{{1,2}})\s*(?:de\s+)?({_MN})\.?\s*(?:de\s+)?(\d{{4}}|\d{{2}})")
_MES_CARPETA = re.compile(rf"({_MN})(?![a-z])")


def _iso(a, m, d):
    try: return datetime.date(a, m, d).isoformat()
    except ValueError: return None


def fecha_de_carpeta(ruta: str, anio: int | None = None) -> str | None:
    """ISO de la carpeta más honda con fecha completa; si no hay, carpeta de solo el día + mes de una carpeta de arriba + `anio`
    (sin `anio`, el de hoy). None si la ruta no dice día y mes (o la fecha no existe)."""
    partes = [norm(p).strip() for p in re.split(r"[\\/]", ruta or "")[:-1]]
    for p in reversed(partes):
        m = _CARPETA.fullmatch(p)
        if m: return _iso(int(m.group(3)) + (2000 if len(m.group(3)) == 2 else 0), _MES[m.group(2)], int(m.group(1)))
    for i in range(len(partes) - 1, -1, -1):
        if not re.fullmatch(r"\d{1,2}", partes[i]): continue
        mes = next((_MES_CARPETA.match(p) for p in reversed(partes[:i]) if _MES_CARPETA.match(p)), None)
        return _iso(anio or datetime.date.today().year, _MES[mes.group(1)], int(partes[i])) if mes else None
    return None


def aplicar_fecha_carpeta(docs: list, ruta: str) -> list:
    """Pone la fecha de la carpeta en cada papel; si la impresa (leída) era otra, la guarda en `fecha_impresa` y avisa."""
    from collections import Counter
    anios = Counter(d["fecha"][:4] for d in docs if re.match(r"\d{4}-", d.get("fecha") or ""))
    f = fecha_de_carpeta(ruta, int(anios.most_common(1)[0][0]) if anios else None)
    if not f: return docs
    dmy = lambda iso: "/".join(reversed(iso.split("-")))
    for d in docs:
        if d.get("fecha") and d["fecha"] != f:
            d["fecha_impresa"] = d["fecha"]
            d.setdefault("avisos", []).append(f"Fecha impresa {dmy(d['fecha'])} distinta de la carpeta {dmy(f)}: se usa la de la carpeta")
        d["fecha"] = f
    return docs


def leer_texto(texto: str, categoria: str = "") -> list:
    """Texto de una foto o página → lista de documentos (uno por papel).
    categoria = lo que tú dijiste al subirlo (o la carpeta): «cierre», «comandas» o «gastos» (vacío = detectarlo)."""
    out = []
    for p in separar(texto):
        t = detectar_tipo(p); aviso = ""
        if categoria in ("cierre", "comandas"):
            # el cierre se imprime en varias hojas y las intermedias no traen el membrete (hablan de meseros, ventas por hora…): lo que dices manda
            forzado = FAMILIA[categoria][0]
            if t in ("gasto_caja", "caja_menor_manuscrito"): aviso = f"Lo subiste como «{categoria}» pero parece {t.replace('_', ' ')}: revisa el tipo"
            if not (categoria == "comandas" and t == "rappi"): t = forzado   # el papel de Rappi es de la familia de comandas: no se fuerza a venta
        elif categoria and t != "otro" and t not in FAMILIA.get(categoria, ()):
            aviso = f"Lo subiste como «{categoria}» pero parece {t.replace('_', ' ')}: se dejó como lo que parece"
        elif categoria and t == "otro": t = FAMILIA["gastos"][-1]
        if t == "otro":
            d = _base("otro", p); d["avisos"].append("No se reconoció el tipo de papel"); d["contar"] = False
            if len(p) < 25: continue
            out.append(d)
        else:
            d = PARSERS[t](p)
            if aviso: d["avisos"].append(aviso)
            out.append(d)
    return out
