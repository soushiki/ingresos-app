"""Prueba del libro contable con el texto que leería el OCR de TUS papeles (recibo de venta, gastos de caja, factura)."""
import io, sys
from parser_module.contable import abreviar_recibos, construir, leer_texto, rangos, libro_a_excel, Clasificador

from parser_module.contable.ejemplos import FOTO_PAPELES, GASTO, VENTA
ok = True
def chk(c, m):
    global ok; ok &= bool(c); print(("✓ " if c else "✗ ") + m)

docs = leer_texto(FOTO_PAPELES) + leer_texto(VENTA)
chk([d["tipo"] for d in docs] == ["gasto_caja", "caja_menor_manuscrito", "gasto_caja", "caja_menor_manuscrito", "gasto_caja", "caja_menor_manuscrito", "factura", "venta"],
    f"8 papeles reconocidos (6 de una sola foto): {[d['tipo'][:6] for d in docs]}")
v = docs[-1]
chk((v["numero"], v["consumo"], v["propina"], v["efectivo"], v["tarjeta"], v["fecha"]) == ("85531", 178000, 17800, 100000, 95800, "2026-09-12"), f"recibo de venta: {v['numero']} · consumo {v['consumo']} · propina {v['propina']} · efectivo {v['efectivo']} · tarjeta {v['tarjeta']}")
chk(not v["avisos"], "los pagos cuadran con consumo + propina")
g = {d["numero"]: d for d in docs if d["tipo"] == "gasto_caja"}
chk((g["220"]["valor"], g["217"]["valor"], g["216"]["valor"]) == (26000, 86000, 2800) and "transportes de compras" in g["220"]["detalle"], "gastos de caja: valor, consecutivo y descripción")
f = docs[6]
chk((f["valor"], f["numero"], f["tercero"], f["medio"]) == (10000, "POS67085", "Sebastian Hernandez De La Espriella", "Transferencia"), f"factura: {f['tercero']} · {f['valor']} · {f['medio']} (la nota a mano «Transf» manda sobre «Efectivo»)")

cl = Clasificador()
for d in docs:
    if d["tipo"] in ("gasto_caja", "factura"):
        r = cl.clasificar(d["tercero"] if d["tipo"] == "factura" else "", d["detalle"], d["texto"]); d["cuenta"], d["conf"] = r["cuenta"], r["conf"]
        print(f"     {d['numero']:<8} → {r['cuenta'] or '—':<9} ({r['conf']:.2f}) {r['motivo']}")
chk(g["220"]["cuenta"] == "51355001" and g["217"]["cuenta"] == "28150501" and f["cuenta"] == "51953001", "transporte → 51355001 · pago a domicilio → 28150501 · papel → 51953001")
chk(g["216"]["conf"] < 0.75, "«pilas»: cuenta dudosa → la app te pide confirmar")
r = construir("2026-09-12", docs)
for x in r["filas"]: print(f"     {x['codigo']:<9}{x['nombre'][:26]:<27}{x['tercero'][:22]:<23}{x['descripcion'][:34]:<35}{x['debito']:>9,}{x['credito']:>9,}")
chk(sum(1 for d in r["documentos"] if not d["contar"]) == 3, "los 3 recibos manuscritos se detectan como duplicados de los impresos")
chk(r["diferencia"] == 0 and r["debito"] == 320600, f"el día cuadra (la parte con tarjeta, 95.800, también entra): débito {r['debito']:,} = crédito {r['credito']:,}")
caja = [x for x in r["filas"] if x["tercero"] == "Cuantías menores"]
chk(caja[-1]["descripcion"] == "Recibos: 216, 217 y 220" and caja[-1]["credito"] == 114800, "caja menor: «Recibos: 216, 217 y 220» y un crédito a Efectivo por 114.800")
ef = [x for x in r["filas"] if x["tercero"] == "Consumidor Final" and x["medio"] == "Efectivo"]
chk([(x["codigo"], x["debito"], x["credito"]) for x in ef] == [("11050501", 100000, 0), ("28150502", 0, 17800), ("41401501", 0, 82200)], "efectivo 100.000 = propina 17.800 + restaurante 82.200 (la tarjeta cubre primero el consumo)")
tj = [(x["codigo"], x["debito"], x["credito"]) for x in r["filas"] if x["tercero"] == "Consumidor Final" and x["medio"] != "Efectivo"]
chk(tj == [("11200501", 95800, 0), ("41401501", 0, 95800)], f"la parte con tarjeta: Banco 95.800 contra Restaurante: {tj}")

# comandas pagadas con VISA, transferencia sin cifra, Nequi, Rappi y crédito personal (fiado)
def cmd(n, pago, extra=""):
    return "\n".join(["SU RESTAURANTE", f"RECIBO #: {n}", "Fecha de Venta: 16/09/2026 9:00:00 p. m.", extra + "SUBTOTAL CONSUMO $40,000", "**TOTAL CONSUMO>> $50000",
                      "DESCUENTO $10,000", "*TOTAL A PAGAR> $40,000", "PROPINA $", "PAGADO $40,000", pago, "CAMBIO $"])
vv = [leer_texto(cmd(90001, "PAGA CON VISA $40,000"))[0], leer_texto(cmd(90002, "PAGA CON TRANSFEREN"))[0], leer_texto(cmd(90003, "PAGA CON NEQUI $40,0"))[0],
      leer_texto(cmd(90004, "PAGA CON RAPPI $40,000"))[0], leer_texto(cmd(90005, "PAGA CON CRED.PERSONA $40,000", extra="Cliente: ANA PEREZ\n"))[0]]
chk([(x["consumo"], x["tarjeta"], x["transf"], x["credito"], x["medio"]) for x in vv] ==
    [(40000, 40000, 0, 0, "Tarjeta"), (40000, 0, 40000, 0, "Transferencia"), (40000, 0, 40000, 0, "Nequi"), (40000, 0, 40000, 0, "Rappi"), (40000, 0, 0, 40000, "Crédito personal")],
    "VISA = tarjeta · transferencia sin cifra o cortada = lo pagado · Nequi · Rappi · CRED.PERSONA = fiado (no tarjeta) · el descuento no se resta dos veces")
r4 = construir("2026-09-16", vv)
deb = {(x["codigo"], x["medio"]): x["debito"] for x in r4["filas"] if x["debito"]}
chk(deb == {("11200501", "Tarjeta"): 40000, ("11200501", "Transferencia"): 40000, ("11200501", "Nequi"): 40000, ("13452501", "App"): 40000, ("13050501", "Crédito personal"): 40000}
    and [x["credito"] for x in r4["filas"] if x["codigo"] == "41401501"] == [200000] and r4["diferencia"] == 0,
    "tarjeta/transferencia/Nequi → Banco · Rappi → Ingresos por cobrar · fiado → Cuenta por cobrar · Restaurante 200.000")
fx = leer_texto("Factura de venta No. FV123\nCLIENTE: Samu\nTomate 20.000\nTotal Factura: $ 124,400\n")[0]
chk(fx["valor"] == 124400, f"«Total Factura: $ 124,400» → {fx['valor']}")

# comanda mal leída: el efectivo no alcanza para propina + domicilio → no se acredita más de lo que entró
vm = dict(v, id="mal", numero="85599", efectivo=10000, tarjeta=0, domicilio=5000, avisos=[])
r5 = construir("2026-09-12", [vm])
ef5 = [(x["codigo"], x["debito"], x["credito"]) for x in r5["filas"] if x["medio"] == "Efectivo" and (x["debito"] or x["credito"])]
chk(ef5 == [("11050501", 10000, 0), ("28150502", 0, 10000)] and r5["diferencia"] == 0 and any("no alcanza" in a for a in r5["avisos"]),
    f"efectivo 10.000 < propina 17.800 + domicilio 5.000: propina tope 10.000, domicilio 0, el día cuadra y se avisa: {ef5}")

# recaudos del banco: las cifras de tu día 12/09
r2 = construir("2026-09-12", [], {"llave": 730550, "tarjetas": 146500, "qr": 1091950})
chk([x["credito"] for x in r2["filas"] if x["credito"]] == [1969000] and r2["diferencia"] == 0, "recaudos del banco: Restaurante 1.969.000 = 730.550 + 146.500 + 1.091.950")
chk(abreviar_recibos(["85531", "85533", "85534", "85540"]) == "85531, 533, 534, 540" and rangos([210, 211, 212, 213]) == "210 al 213" and rangos([208, 209, 214]) == "208, 209 y 214", "frases de descripción como las escribes")
# día que no cuadra
d_mal = leer_texto(GASTO.format(n=300, v="5,000", d="algo raro"))
r3 = construir("2026-09-13", d_mal)
chk(any("sin cuenta" in a for a in r3["avisos"]) and r3["diferencia"] == 0, "un gasto sin cuenta se avisa (no se inventa una)")
# cuentas puente (R10): nada se descarta en silencio y ninguna fila queda sin código
from parser_module.contable.asientos import CFG as CFG_A
PI, PG = CFG_A["puente_ingreso"], CFG_A["puente_gasto"]
chk(r3["filas"] and all(x["codigo"] for x in r3["filas"]) and r3["filas"][0]["codigo"] == PG, f"gasto de caja sin cuenta → {PG} (puente_gasto), ninguna fila sin código")
vs = dict(v, id="sinmedio", numero="85600", efectivo=0, tarjeta=0, transf=0, credito=0, avisos=[])
r6 = construir("2026-09-12", [vs])
p6 = [(x["codigo"], x["debito"], x["credito"]) for x in r6["filas"]]
chk(p6 == [(PI, 178000, 0), ("41401501", 0, 178000)] and r6["diferencia"] == 0 and any("puente" in a for a in r6["avisos"]),
    f"venta sin medio de pago → débito {PI} (puente_ingreso) contra Restaurante y aviso: {p6}")
fs = dict(f, id="sinvalor", valor=0, avisos=[])
fc = dict(f, id="sincuenta", numero="POS1", cuenta="", avisos=[])
r7 = construir("2026-09-12", [fs, fc])
chk([(p["id"], p["valor"]) for p in r7["pendientes"]] == [("sinvalor", 0)] and any("pendiente" in a for a in r7["avisos"]) and r7["diferencia"] == 0,
    "factura sin valor → queda en pendientes con valor 0 y aviso (no se inventa un asiento)")
chk([x["codigo"] for x in r7["filas"]] == [PG, "11200501"], "factura sin cuenta → puente_gasto contra Bancos")
dias = [r, r3, r4, r5, r6, r7]
contados = [d["id"] for x in dias for d in x["documentos"] if d.get("contar") and d["tipo"] != "cierre"]
en_libro = {p["id"] for x in dias for p in x["pendientes"]} | {i for x in dias for f_ in x["filas"] for i in f_["docs"]}
chk(set(contados) <= en_libro, f"ningún papel desaparece de construir: {sorted(set(contados) - en_libro) or 'todos están'}")
# Excel
x = libro_a_excel({"2026-09-12": r["filas"] + r2["filas"]}, "Mi restaurante", "900.000.000-1")
import tempfile, os; open(os.path.join(tempfile.gettempdir(), "libro_prueba.xlsx"), "wb").write(x)
print("\n" + ("TODO OK" if ok else "HAY FALLOS"))
