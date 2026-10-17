"""Documentos del día → filas del libro (débito/crédito) con tus cuentas y tus frases."""
from __future__ import annotations
import json, re
from collections import defaultdict
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
CFG = {"reporta_efectivo": "Yorly", "reporta_banco": "Sergio", "cuenta_recaudo": ""}


def nombre(cod: str) -> str:
    return CATALOGO.get(cod, {}).get("nombre_diario") or ("SIN CLASIFICAR" if not cod else cod)


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


def marcar_duplicados(docs: list) -> list:
    """El gasto de caja impreso y su «recibo de caja menor» manuscrito son el MISMO gasto: se cuenta uno solo."""
    vistos = {}
    for d in docs:
        if d.get("tipo") == "gasto_caja" and d.get("numero"):
            if d["numero"] in vistos: d["dup_de"] = vistos[d["numero"]]
            else: vistos[d["numero"]] = d["id"]
        if d.get("tipo") == "venta" and d.get("numero"):
            k = "v" + d["numero"]
            if k in vistos: d["dup_de"] = vistos[k]
            else: vistos[k] = d["id"]
    impresos = {(x["valor"], x["id"]) for x in docs if x.get("tipo") == "gasto_caja" and not x.get("dup_de")}
    usados = set()
    for d in docs:
        if d.get("tipo") == "caja_menor_manuscrito":
            par = next(((v, i) for v, i in sorted(impresos) if v == d.get("valor") and i not in usados), None)
            if par: usados.add(par[1]); d["dup_de"] = par[1]
            else: d["dup_de"] = ""
    for d in docs:
        if not d.get("manual_contar"): d["contar"] = not d.get("dup_de") and d.get("tipo") not in ("otro", "cierre")
    return docs


def construir(fecha: str, docs: list, banco: dict | None = None, cfg: dict | None = None, cierre: dict | None = None) -> dict:
    cfg = {**CFG, **(cfg or {})}; banco = banco or {}; filas, avisos = [], []
    todos = marcar_duplicados(docs); completar_desde_cierre(todos)
    docs = [d for d in todos if d.get("contar") and d["tipo"] != "cierre"]

    def fila(cod, tercero, desc, deb=0, cre=0, reporta="", medio="", grupo=""):
        filas.append(dict(fecha=fecha, codigo=cod, nombre=nombre(cod), tercero=tercero, descripcion=desc, debito=int(deb), credito=int(cre), reporta=reporta, medio=medio, grupo=grupo))

    # 1) recaudos del banco (de tu extracto). Si escribiste alguno, el extracto manda sobre lo que dicen las comandas pagadas al banco.
    total_b = 0
    for k, desc, medio in RECAUDOS_BANCO:
        v = int(banco.get(k) or 0)
        if v: fila(BANCO, "Consumidor Final", desc, deb=v, reporta=cfg["reporta_banco"], medio=medio, grupo="venta"); total_b += v
    if total_b:
        cta = f"Recaudos pagados a la cta.{cfg['cuenta_recaudo']}" if cfg["cuenta_recaudo"] else "Recaudos pagados a la cuenta"
        fila(RESTAURANTE, "Consumidor Final", cta, cre=total_b, reporta=cfg["reporta_banco"], grupo="venta")
    rappi_b = int(banco.get("rappi") or 0)
    if rappi_b:   # Rappi te consigna lo que te debía: entra al banco y baja la cuenta por cobrar (no es una venta nueva)
        fila(BANCO, "Rappi", "Pagos interbancarios Rappi", deb=rappi_b, reporta=cfg["reporta_banco"], medio="Transferencia", grupo="venta")
        fila(POR_COBRAR, "Rappi", "Pagos interbancarios Rappi", cre=rappi_b, reporta=cfg["reporta_banco"], grupo="venta")

    # 2) ventas en efectivo (comandas): solo lo que entró en efectivo; la propina/domicilio pagados por tarjeta o app no pasan por la caja
    ventas = [d for d in docs if d["tipo"] == "venta"]
    R = {d["id"]: repartir(d) for d in ventas}
    if ventas:
        efe = sum(d["efectivo"] for d in ventas); pro = sum(R[d["id"]]["cash_tip"] for d in ventas); dom = sum(R[d["id"]]["cash_dom"] for d in ventas)
        for d in ventas:
            if d["propina"] > d["efectivo"] + d["tarjeta"] + d["transf"] + d.get("credito", 0): avisos.append(f"Recibo {d['numero']}: la propina ({d['propina']:,}) es mayor que lo pagado".replace(",", "."))
        if efe:
            if pro + dom > efe:   # el efectivo leído no alcanza (comanda mal leída): no se acredita más de lo que entró, para que el día cuadre
                avisos.append("El efectivo no alcanza para cubrir propinas y domicilios")
                pro = min(pro, efe); dom = min(dom, efe - pro)
            fila(EFECTIVO, "Consumidor Final", "Ordenes: " + abreviar_recibos(d["numero"] for d in ventas if d["efectivo"]), deb=efe, reporta=cfg["reporta_efectivo"], medio="Efectivo", grupo="venta")
            if pro: fila(PROPINAS, "Consumidor Final", "Ordenes: " + abreviar_recibos(d["numero"] for d in ventas if R[d["id"]]["cash_tip"]), cre=pro, reporta=cfg["reporta_efectivo"], medio="Efectivo", grupo="venta")
            if dom: fila(DOMICILIOS, "Consumidor Final", "Ordenes: " + abreviar_recibos(d["numero"] for d in ventas if R[d["id"]]["cash_dom"]), cre=dom, reporta=cfg["reporta_efectivo"], medio="Efectivo", grupo="venta")
            fila(RESTAURANTE, "Consumidor Final", "Recaudos en efectivo", cre=efe - pro - dom, reporta=cfg["reporta_efectivo"], medio="Efectivo", grupo="venta")

    # 2b) ventas que no entraron en efectivo: tarjeta y transferencias/QR/Nequi/Bre-B → banco (salvo que hayas escrito el extracto),
    #     Rappi → ingresos por cobrar, crédito personal (fiado) → cuenta por cobrar al cliente. La propina y el domicilio pagados así
    #     se separan igual que en el efectivo.
    if ventas:
        partes = []   # (cuenta, tercero, medio, comanda, monto)
        for d in ventas:
            if d.get("tarjeta") and not total_b: partes.append((BANCO, "Consumidor Final", "Tarjeta", d, d["tarjeta"]))
            if d.get("transf"):
                m = d.get("medio_transf") or "Transferencia"
                if m == "Rappi": partes.append((POR_COBRAR, "Rappi", "App", d, d["transf"]))
                elif not total_b: partes.append((BANCO, "Consumidor Final", m, d, d["transf"]))
            if d.get("credito"): partes.append((CXC_CLIENTES, d.get("cliente") or "Cliente (crédito personal)", "Crédito personal", d, d["credito"]))
        if total_b:
            al_banco = sum(d.get("tarjeta", 0) + (d.get("transf", 0) if (d.get("medio_transf") or "") != "Rappi" else 0) for d in ventas)
            if al_banco and al_banco != total_b:
                avisos.append(f"Recaudos del extracto ({total_b:,}) ≠ comandas pagadas con tarjeta/transferencia ({al_banco:,}); se usó el extracto".replace(",", "."))
        grupos = defaultdict(list)
        for p in partes: grupos[p[:3]].append(p)
        rep = cfg["reporta_banco"]
        for (cod, ter, medio), ps in grupos.items():
            ords = "Ordenes: " + abreviar_recibos(p[3]["numero"] for p in ps if p[3]["numero"])
            desc = RECAUDO_DESC.get(medio, f"Recaudos por {medio}") + (" · " + ords if ords != "Ordenes: " else "")
            fila(cod, ter, desc, deb=sum(p[4] for p in ps), reporta=rep, medio=medio, grupo="venta")
        if partes:
            pro_e = dom_e = 0; nums_p, nums_d = set(), set()
            for cod, ter, medio, d, v in partes:   # la propina/domicilio no pagados en efectivo se reparten según lo que puso cada medio
                r = R[d["id"]]; tot = d.get("tarjeta", 0) + d.get("transf", 0) + d.get("credito", 0)
                p_, d_ = round(r["tip_e"] * v / tot), round(r["dom_e"] * v / tot)
                pro_e += p_; dom_e += d_
                if p_: nums_p.add(d["numero"])
                if d_: nums_d.add(d["numero"])
            total_e = sum(p[4] for p in partes)
            if pro_e: fila(PROPINAS, "Consumidor Final", "Ordenes: " + abreviar_recibos(nums_p), cre=pro_e, reporta=rep, grupo="venta")
            if dom_e: fila(DOMICILIOS, "Consumidor Final", "Ordenes: " + abreviar_recibos(nums_d), cre=dom_e, reporta=rep, grupo="venta")
            fila(RESTAURANTE, "Consumidor Final", "Recaudos con tarjeta, transferencias, apps y crédito", cre=total_e - pro_e - dom_e, reporta=rep, grupo="venta")
        for d in ventas:
            if d.get("consumo") and not d.get("cortesia") and not (d["efectivo"] + d["tarjeta"] + d["transf"] + d.get("credito", 0)):
                avisos.append(f"Recibo {d['numero'] or 's/n'}: no se leyó con qué se pagó ({d['consumo']:,}); no entra al libro".replace(",", "."))

    # 3) caja menor: un renglón por cuenta + un crédito a Efectivo
    cm = [d for d in docs if d["tipo"] in ("gasto_caja", "caja_menor_manuscrito") and d["medio"] in ("", "Efectivo")]
    por_cuenta = defaultdict(list)
    for d in cm: por_cuenta[d.get("cuenta", "")].append(d)
    for cod, ds in sorted(por_cuenta.items(), key=lambda kv: (kv[0] == "", kv[0])):
        if not cod: avisos.append(f"{len(ds)} gasto(s) de caja sin cuenta: " + ", ".join(d["numero"] or "s/n" for d in ds))
        fila(cod, "Cuantías menores", "Recibos: " + rangos(d["numero"] for d in ds if d["numero"]), deb=sum(d["valor"] for d in ds), reporta=cfg["reporta_efectivo"], medio="Efectivo", grupo="gasto")
    if cm:
        fila(EFECTIVO, "Cuantías menores", "Recibos: " + rangos(d["numero"] for d in cm if d["numero"]), cre=sum(d["valor"] for d in cm), reporta=cfg["reporta_efectivo"], medio="Efectivo", grupo="gasto")

    # 4) facturas y gastos pagados por banco o en efectivo, uno por uno (si no se leyó el valor, no se inventa un asiento en cero)
    for d in docs:
        if d["tipo"] == "factura" and not d["valor"]:
            avisos.append(f"Factura {d['numero'] or d['tercero'] or 's/n'}: sin valor leído, no genera asientos (corrígela o desmárcala)"); continue
        if d["tipo"] == "factura" or (d["tipo"] in ("gasto_caja", "caja_menor_manuscrito") and d["medio"] not in ("", "Efectivo")):
            if not d["valor"]: avisos.append(f"Factura {d['numero'] or d['tercero'] or 's/n'}: sin valor, no se contabilizó"); continue
            if d["medio"] in ("Tarjeta", "Mixto"): avisos.append(f"Factura {d['numero'] or d['tercero'] or 's/n'}: pagada con tarjeta; se registró contra Bancos, revisa el medio")
            if not d["cuenta"]: avisos.append(f"Factura {d['numero'] or d['tercero'] or 's/n'}: falta la cuenta")
            ef = d["medio"] == "Efectivo"; rep = cfg["reporta_efectivo"] if ef else cfg["reporta_banco"]
            desc = d.get("detalle") or "Compra"; ter = d["tercero"] or "Proveedor"
            fila(d["cuenta"], ter, desc, deb=d["valor"], reporta=rep, medio=d["medio"], grupo="gasto")
            fila(EFECTIVO if ef else BANCO, ter, desc, cre=d["valor"], reporta=rep, medio=d["medio"], grupo="gasto")
    for d in docs:
        if d["tipo"] in ("venta", "gasto_caja", "factura") and d.get("avisos") and not d.get("revisado"):
            avisos += [f"{d['tipo'].replace('_', ' ').capitalize()} {d['numero'] or ''}: {a}".replace("  ", " ") for a in d["avisos"]]
    cie = {**datos_cierre(todos), **{k: int(v) for k, v in (cierre or {}).items() if v is not None}}
    cruces, faltan = cruzar([d for d in todos if d["tipo"] != "cierre"], cie)
    if faltan: avisos.insert(0, "Faltan comandas del cierre: " + ", ".join(map(str, faltan)))
    if faltan: avisos.append("Falta la comanda " + ", ".join(map(str, faltan)) + " (está en el rango del cierre)")
    if any(not x["ok"] for x in cruces): avisos.append(f"El cierre del POS no coincide con tus papeles en {sum(not x['ok'] for x in cruces)} concepto(s): ¿falta alguna comanda o se leyó mal?")
    deb, cre = sum(f["debito"] for f in filas), sum(f["credito"] for f in filas)
    if deb != cre: avisos.insert(0, f"El día no cuadra: débito {deb:,} · crédito {cre:,} (diferencia {deb - cre:,})".replace(",", "."))
    return dict(filas=filas, debito=deb, credito=cre, diferencia=deb - cre, avisos=avisos, documentos=todos, cierre=cie, cruces=cruces, faltan=faltan)
