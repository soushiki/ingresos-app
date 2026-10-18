"""Spike ADR-002 (T4): MOVIMIENTOS con fórmulas sobre DATOS OCR.
Para cada día de libro.json: arma DATOS OCR (una fila por papel y medio de pago), escribe cada importe como fórmula
y la evalúa con un mini-evaluador (refs, SUMIFS de igualdad, MIN, +/-) para compararla con construir()."""
import copy, json, sys, zipfile, io
from collections import defaultdict
from datetime import date
sys.path.insert(0, sys.argv[1])
from openpyxl import Workbook
from parser_module.contable import asientos as A

lib = json.load(open(f"{sys.argv[1]}/datos/libro.json", encoding="utf-8"))
D = "'DATOS OCR'!"
COLS = ["fecha", "archivo", "tipo", "numero", "tercero", "detalle", "valor", "medio", "cuenta", "estado", "aviso", "propina", "domicilio", "bloque"]
C = {k: chr(65 + i) for i, k in enumerate(COLS)}


class F:   # fórmula con su valor
    def __init__(s, txt, v): s.txt, s.v = txt, v
    def __add__(s, o): return F(f"{s.txt}+{o.txt}", s.v + o.v)
    def __sub__(s, o): return F(f"{s.txt}-({o.txt})", s.v - o.v)


def armar(fecha, dia):
    cfg = A.CFG; banco = dia.get("banco") or {}
    todos = A.marcar_duplicados(copy.deepcopy(dia["documentos"])); A.completar_desde_cierre(todos)
    datos = []   # dicts con COLS
    def dato(**k):
        r = dict(fecha=fecha, archivo="", tipo="", numero="", tercero="", detalle="", valor=0, medio="", cuenta="", estado="ok", aviso="", propina=0, domicilio=0, bloque="", **{})
        r.update(k); datos.append(r); return len(datos) + 1   # fila en la hoja (encabezado en 1)
    def ref(fila, col="valor"): return F(f"{D}{C[col]}{fila}", datos[fila - 2][col])
    def sumifs(col, **crit):
        cr = dict(fecha=fecha, estado="ok", **crit)
        txt = f"SUMIFS({D}{C[col]}:{C[col]}," + ",".join(f'{D}{C[k]}:{C[k]},' + (f"$A{{fila}}" if k == "fecha" else f'"{v}"') for k, v in cr.items()) + ")"
        v = sum(r[col] for r in datos if all((r[k] != v[2:] if str(v).startswith("<>") else r[k] == v) for k, v in cr.items()))
        return F(txt, v)
    movs = []   # (codigo, tercero, desc, debito F|None, credito F|None)
    def mov(cod, ter, desc, deb=None, cre=None): movs.append((cod, ter, desc, deb, cre)); return deb or cre

    for d in todos:   # papeles que no cuentan: se ven, pero no suman
        if not d.get("contar") or d["tipo"] == "cierre":
            dato(archivo=d.get("origen", ""), tipo=d["tipo"], numero=d.get("numero", ""), tercero=d.get("tercero", ""), valor=d.get("valor") or d.get("consumo") or 0,
                 estado="no cuenta", aviso=("duplicado de " + d["dup_de"]) if d.get("dup_de") else ("cierre" if d["tipo"] == "cierre" else "desmarcado"))
    docs = [d for d in todos if d.get("contar") and d["tipo"] != "cierre"]
    total_b = 0; ext = []
    for k, desc, medio in A.RECAUDOS_BANCO:
        v = int(banco.get(k) or 0)
        if v: ext.append(mov(A.BANCO, "Consumidor Final", desc, deb=ref(dato(tipo="extracto", archivo="extracto bancario", detalle=desc, valor=v, medio=medio, cuenta=A.BANCO, bloque="extracto")))); total_b += v
    if ext: mov(A.RESTAURANTE, "Consumidor Final", "Recaudos", cre=sum(ext[1:], ext[0]))
    if int(banco.get("rappi") or 0):
        r = ref(dato(tipo="extracto", archivo="extracto bancario", detalle="Rappi", valor=int(banco["rappi"]), medio="Transferencia", cuenta=A.BANCO, bloque="rappi"))
        mov(A.BANCO, "Rappi", "Rappi", deb=r); mov(A.POR_COBRAR, "Rappi", "Rappi", cre=r)

    ventas = [d for d in docs if d["tipo"] == "venta"]; R = {d["id"]: A.repartir(d) for d in ventas}
    for d in ventas:   # una fila por papel y medio
        base = dict(archivo=d.get("origen", ""), tipo="venta", numero=d["numero"], detalle=d.get("detalle", ""), bloque="venta")
        r = R[d["id"]]; tot = d.get("tarjeta", 0) + d.get("transf", 0) + d.get("credito", 0)
        if d["efectivo"] or r["cash_tip"] or r["cash_dom"]: dato(**base, tercero="Consumidor Final", valor=d["efectivo"], medio="Efectivo", cuenta=A.EFECTIVO, propina=r["cash_tip"], domicilio=r["cash_dom"])
        partes = []
        if d.get("tarjeta"): partes.append((A.BANCO, "Consumidor Final", "Tarjeta", d["tarjeta"], bool(total_b)))
        if d.get("transf"):
            m = d.get("medio_transf") or "Transferencia"
            partes.append((A.POR_COBRAR, "Rappi", "App", d["transf"], False) if m == "Rappi" else (A.BANCO, "Consumidor Final", m, d["transf"], bool(total_b)))
        if d.get("credito"): partes.append((A.CXC_CLIENTES, d.get("cliente") or "Cliente (crédito personal)", "Crédito personal", d["credito"], False))
        for cod, ter, medio, v, en_ext in partes:
            dato(**base, tercero=ter, valor=v, medio=medio, cuenta=cod, estado="en extracto" if en_ext else "ok", aviso="lo cubre el extracto" if en_ext else "",
                 propina=round(r["tip_e"] * v / tot), domicilio=round(r["dom_e"] * v / tot))
        if d.get("consumo") and not d.get("cortesia") and not tot + d["efectivo"]:
            dato(**base, tercero="Consumidor Final", valor=d["consumo"], medio="(sin medio)", cuenta=cfg["puente_ingreso"], aviso="no se leyó el medio de pago")
    if ventas:
        efe = sumifs("valor", bloque="venta", cuenta=A.EFECTIVO)
        if efe.v:
            mov(A.EFECTIVO, "Consumidor Final", "Ordenes", deb=efe)
            pro = F(f"MIN({sumifs('propina', bloque='venta', cuenta=A.EFECTIVO).txt},{efe.txt})", 0); pro.v = min(sumifs('propina', bloque='venta', cuenta=A.EFECTIVO).v, efe.v)
            dom = F(f"MIN({sumifs('domicilio', bloque='venta', cuenta=A.EFECTIVO).txt},{(efe - pro).txt})", 0); dom.v = min(sumifs('domicilio', bloque='venta', cuenta=A.EFECTIVO).v, efe.v - pro.v)
            if pro.v: mov(A.PROPINAS, "Consumidor Final", "Ordenes", cre=pro)
            if dom.v: mov(A.DOMICILIOS, "Consumidor Final", "Ordenes", cre=dom)
            mov(A.RESTAURANTE, "Consumidor Final", "Recaudos en efectivo", cre=efe - pro - dom)
        grupos = list(dict.fromkeys((r["cuenta"], r["tercero"], r["medio"]) for r in datos if r["bloque"] == "venta" and r["estado"] == "ok" and r["cuenta"] not in (A.EFECTIVO, cfg["puente_ingreso"])))
        partes = [mov(cod, ter, medio, deb=sumifs("valor", bloque="venta", cuenta=cod, tercero=ter, medio=medio)) for cod, ter, medio in grupos]
        if partes:
            no_ef = dict(bloque="venta", cuenta="<>" + A.EFECTIVO)
            pro_e, dom_e = sumifs("propina", **no_ef), sumifs("domicilio", **no_ef)
            if pro_e.v: mov(A.PROPINAS, "Consumidor Final", "Ordenes", cre=pro_e)
            if dom_e.v: mov(A.DOMICILIOS, "Consumidor Final", "Ordenes", cre=dom_e)
            mov(A.RESTAURANTE, "Consumidor Final", "Recaudos electrónicos", cre=sum(partes[1:], partes[0]) - pro_e - dom_e)
        pu = sumifs("valor", bloque="venta", cuenta=cfg["puente_ingreso"])
        if pu.v: mov(cfg["puente_ingreso"], "Consumidor Final", "Venta sin medio", deb=pu); mov(A.RESTAURANTE, "Consumidor Final", "Venta sin medio", cre=pu)

    cm = [d for d in docs if d["tipo"] in ("gasto_caja", "caja_menor_manuscrito") and d["medio"] in ("", "Efectivo")]
    for d in cm: dato(archivo=d.get("origen", ""), tipo=d["tipo"], numero=d["numero"], tercero=d["tercero"], detalle=d.get("detalle", ""), valor=d["valor"], medio="Efectivo",
                      cuenta=d.get("cuenta") or cfg["puente_gasto"], aviso="" if d.get("cuenta") else "falta la cuenta", bloque="caja")
    cods = sorted({d.get("cuenta", "") for d in cm}, key=lambda c: (c == "", c))
    caja = [mov(c or cfg["puente_gasto"], "Cuantías menores", "Recibos", deb=sumifs("valor", bloque="caja", cuenta=c or cfg["puente_gasto"])) for c in cods]
    if caja: mov(A.EFECTIVO, "Cuantías menores", "Recibos", cre=sum(caja[1:], caja[0]))
    for d in docs:
        if d["tipo"] == "factura" or (d["tipo"] in ("gasto_caja", "caja_menor_manuscrito") and d["medio"] not in ("", "Efectivo")):
            f = dato(archivo=d.get("origen", ""), tipo=d["tipo"], numero=d["numero"], tercero=d["tercero"], detalle=d.get("detalle", ""), valor=d["valor"], medio=d["medio"],
                     cuenta=d["cuenta"] or cfg["puente_gasto"], estado="ok" if d["valor"] else "pendiente", aviso="" if d["valor"] else "sin valor leído", bloque="factura")
            if d["valor"]:
                mov(d["cuenta"] or cfg["puente_gasto"], d["tercero"], "Compra", deb=ref(f)); mov(A.EFECTIVO if d["medio"] == "Efectivo" else A.BANCO, d["tercero"], "Compra", cre=ref(f))
    return datos, movs


malos, n_dias, n_movs = [], 0, 0
for fecha in sorted(lib):
    datos, movs = armar(fecha, lib[fecha])
    real = A.construir(fecha, copy.deepcopy(lib[fecha]["documentos"]), lib[fecha].get("banco"), None, lib[fecha].get("cierre"))["filas"]
    got = [(c, (d.v if d else 0), (k.v if k else 0)) for c, _, _, d, k in movs]
    exp = [(f["codigo"], f["debito"], f["credito"]) for f in real]
    n_dias += 1; n_movs += len(got)
    if got != exp: malos.append((fecha, [x for x in got if x not in exp], [x for x in exp if x not in got]))
print(f"{n_dias} días, {n_movs} asientos con fórmula; distintos de construir(): {len(malos)}")
for m in malos[:5]: print(" ", m)

# un día real a xlsx, para abrirlo en Excel
fecha = sys.argv[2] if len(sys.argv) > 2 else "2026-09-20"
datos, movs = armar(fecha, lib[fecha])
wb = Workbook(); ws = wb.active; ws.title = "DATOS OCR"; ws.append(COLS)
for r in datos: ws.append([date.fromisoformat(r["fecha"]) if k == "fecha" else r[k] for k in COLS])
mv = wb.create_sheet("MOVIMIENTOS SEPTIEMBRE"); mv.append(["Fecha", "Código", "Tercero", "Descripción", "Débito", "Crédito", "", "esperado débito", "esperado crédito"])
for i, (c, t, desc, d, k) in enumerate(movs, 2):
    mv.append([date.fromisoformat(fecha), int(c), t, desc, ("=" + d.txt.replace("{fila}", str(i))) if d else 0, ("=" + k.txt.replace("{fila}", str(i))) if k else 0, None, d.v if d else 0, k.v if k else 0])
n = len(movs) + 1
mv.append([None, None, None, "Total", f"=SUM(E2:E{n})", f"=SUM(F2:F{n})", None, f"=SUM(H2:H{n})", f"=SUM(I2:I{n})"])
mv.append([None, None, None, "¿Cuadra con lo esperado?", f'=IF(AND(E{n+1}=H{n+1},F{n+1}=I{n+1},E{n+1}=F{n+1}),"SÍ","NO")'])
buf = io.BytesIO(); wb.save(buf)
out = sys.argv[3]; open(out, "wb").write(buf.getvalue())
z = zipfile.ZipFile(io.BytesIO(buf.getvalue()))
print("vbaProject.bin:", any("vbaProject" in x for x in z.namelist()), "| importes sin fórmula:", sum(1 for _, _, _, d, k in movs if not (d or k)), "| filas DATOS OCR:", len(datos), "| guardado:", out)
print("ejemplo:", movs[0][3].txt.replace("{fila}", "2") if movs[0][3] else movs[0][4].txt)
