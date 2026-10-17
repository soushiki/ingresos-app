"""Prueba de la hoja DATOS OCR (R9, ADR-002): una fila por papel y medio de pago; ningún papel falta, ni los que van a puente."""
import io, zipfile
from openpyxl import load_workbook
from parser_module.contable import construir, leer_texto, libro_a_excel
from parser_module.contable.asientos import CFG, COLS_DATOS
from parser_module.contable.ejemplos import FOTO_PAPELES, GASTO, VENTA
ok = True
def chk(c, m):
    global ok; ok &= bool(c); print(("✓ " if c else "✗ ") + m)

PI, PG = CFG["puente_ingreso"], CFG["puente_gasto"]
docs = leer_texto(FOTO_PAPELES) + leer_texto(VENTA)
v = docs[-1]; f = next(d for d in docs if d["tipo"] == "factura")
docs += [dict(v, id="sinmedio", numero="85600", efectivo=0, tarjeta=0, transf=0, credito=0, avisos=[]), dict(f, id="sinvalor", numero="POS2", valor=0, avisos=[])]
docs += [dict(v, id="ilegible", numero="85601", consumo=0, propina=0, efectivo=0, tarjeta=0, transf=0, credito=0, avisos=[])]
docs += leer_texto(GASTO.format(n=300, v="5,000", d="algo raro"))   # gasto de caja sin cuenta
r = construir("2026-09-12", docs, {"tarjetas": 146500})
D = r["datos"]
chk(set(D[0]) == set(COLS_DATOS), f"columnas de ADR-002: {COLS_DATOS}")
ids = [x["id"] for x in D if x["id"]]
chk(set(ids) == {d["id"] for d in r["documentos"]}, f"cada papel del día tiene su fila: {len(set(ids))} de {len(r['documentos'])}")
p = {x["id"]: x for x in D}
v_ = [x for x in D if x["id"] == v["id"]]
chk([(x["medio"], x["valor"], x["cuenta"], x["estado"]) for x in v_] == [("Efectivo", 100000, "11050501", "ok"), ("Tarjeta", 95800, "11200501", "en extracto")],
    f"venta mixta → 2 filas (efectivo y tarjeta; la tarjeta la cubre el extracto): {[(x['medio'], x['valor'], x['estado']) for x in v_]}")
chk(p["sinmedio"]["cuenta"] == PI and p["sinmedio"]["medio"] == "(sin medio)" and p["sinmedio"]["aviso"], f"venta sin medio → fila en {PI} con aviso")
g = next(x for x in D if x["numero"] == "300")
chk(g["cuenta"] == PG and g["estado"] == "ok" and g["aviso"], f"gasto sin cuenta → fila en {PG} con aviso")
chk(p["ilegible"]["estado"] == "pendiente" and p["ilegible"]["aviso"], "venta sin ninguna cifra leída → fila «pendiente» (no se pierde de vista)")
chk(p["sinvalor"]["estado"] == "pendiente" and p["sinvalor"]["valor"] == 0, "factura sin valor → estado «pendiente»")
dup = [x for x in D if x["estado"] == "no cuenta"]
chk(len(dup) == 3 and all("duplicado" in x["aviso"] for x in dup), f"los 3 manuscritos duplicados se ven como «no cuenta»: {len(dup)}")
ext = [x for x in D if x["tipo"] == "extracto"]
chk([(x["valor"], x["medio"], x["bloque"]) for x in ext] == [(146500, "Tarjeta", "extracto")], "el extracto bancario también es una fila")
# los importes que suman («ok») dan lo mismo que el libro, por bloque
caja = sum(x["valor"] for x in D if x["bloque"] == "caja" and x["estado"] == "ok")
chk(caja == next(x["credito"] for x in r["filas"] if x["tercero"] == "Cuantías menores" and x["credito"]), f"caja menor en DATOS OCR = crédito a Efectivo del libro ({caja:,})")

# Excel: DATOS OCR va primero, con una fila por dato y sin macros
x = libro_a_excel({"2026-09-12": r["filas"]}, datos={"2026-09-12": D})
wb = load_workbook(io.BytesIO(x))
ws = wb.worksheets[0]
filas = [f_ for f_ in ws.iter_rows(min_row=2, values_only=True) if any(f_)]
chk(ws.title == "DATOS OCR" and len(filas) == len(D), f"hoja DATOS OCR primera, {len(filas)} filas = {len(D)} datos")
chk(not any("vbaProject" in n for n in zipfile.ZipFile(io.BytesIO(x)).namelist()), "ADR-002: el libro no trae macros")
chk("DATOS OCR" not in load_workbook(io.BytesIO(libro_a_excel({"2026-09-12": r["filas"]}))).sheetnames, "sin datos no se agrega la hoja (compatibilidad)")
print("\n" + ("TODO OK" if ok else "HAY FALLOS"))
