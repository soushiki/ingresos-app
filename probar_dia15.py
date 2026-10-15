"""Prueba con los NÚMEROS de tu cierre del 15/09 (21 comandas, el cierre y 4 vales), sin datos personales.
Debe encontrar justo lo que ya se sabe de ese día: falta la comanda 85610 ($24.900 en efectivo) y todo lo demás coincide con el cierre."""
from parser_module.contable import Clasificador, construir, leer_texto
from parser_module.contable.asientos import completar_desde_cierre

# (recibo, consumo, domicilio, propina, forma de pago: E efectivo · C tarjeta · T transferencia, pagado, cambio, cortesía)
C = [(85605, 47500, 0, 0, "C"), (85606, 43000, 0, 0, "T"), (85607, 95800, 5000, 0, "T"), (85608, 51500, 0, 5000, "T"), (85609, 72500, 0, 0, "C"),
     (85611, 95500, 0, 9550, "T"), (85612, 161000, 0, 0, "C"), (85613, 112000, 0, 0, "T"), (85614, 30000, 0, 0, "E"), (85615, 71000, 15000, 0, "T"),
     (85616, 238000, 0, 12000, "T"), (85617, 104000, 0, 10400, "T"), (85618, 96000, 0, 9600, "T"), (85619, 26500, 0, 2650, "C"), (85620, 80000, 0, 0, "T"),
     (85621, 35500, 0, 0, "E", 50000, 14500), (85622, 38500, 0, 0, "T"), (85623, 65000, 0, 0, "T"), (85624, 80000, 0, 4000, "E"), (85625, 90500, 0, 4500, "T"),
     (85626, 49800, 0, 0, "X")]
M = {"E": "EFECTIVO", "C": "PAGA CON CREDITO", "T": "PAGA CON TRANSFERENCI"}
def m(v): return f"${v:,}"
def comanda(t):
    n, cons, dom, pro, forma = t[:5]; pagado = t[5] if len(t) > 5 else cons + dom + pro; cambio = t[6] if len(t) > 6 else 0
    cab = f"SU RESTAURANTE\nRECIBO #: {n}\nFecha de Venta: 15/09/2026 7:{n % 60:02d}:00 p. m.\nMesa: M{n % 9 + 1}\nMesero: YORLIN\n| Descripcion | Cant | Valor |\nPLATO | 1 | {cons:,}\n"
    if forma == "X": return cab + f"SUBTOTAL CONSUMO $\n**TOTAL CONSUMO>> {m(cons)}\nDESCUENTO {m(cons)}\n*TOTAL A PAGAR> CORTESIA\nPROPINA $\nPAGADO $\nEFECTIVO\nCAMBIO $"
    pago = f"{M[forma]} {m(pagado)}" if forma != "E" else "EFECTIVO"
    return (cab + f"SUBTOTAL CONSUMO {m(cons)}\n**TOTAL CONSUMO>> {m(cons)}\nDESCUENTO $\n" + (f"DOMICILIO {m(dom)}\n" if dom else "") +
            f"*TOTAL A PAGAR> {m(cons + dom)}\nPROPINA {m(pro) if pro else '$'}\nPAGADO {m(pagado)}\n{pago}\nCAMBIO {m(cambio) if cambio else '$'}")
CIERRE = """CIERRE DE CAJA RESUMIDO
Cierre del:  15-sept-26*
Factura Inicial: 85605
Factura Final: 85626
Transacciones: 22
TOTAL VENDIDO EN EL DIA (A+ $1,658,700
Total Descuentos $49,800
TOTAL TARJETAS sin prop (A) $307,500
TOTAL TARJETAS con prop $310,150
TOTAL INGRESOS CON APP $1,251,850
TOTAL INGRESOS CON APP EFE $
TOTAL PROPINAS CON APP $51,050
Total Propinas $57,700
Total Vendido en Domicilios $166,800
Total Numero de Domicilios $2
Total Pagado en Domicilios $20,000
Propinas en Efectivo $4,000
Propinas por Tarjeta $2,650
Propinas por Transferencias App $51,050
Total Propinas $57,700
-VALORES $ SIN PROPINAS-
BASE DE CAJA $407,800
TOTAL VENTA EN EFECTIVO (B) $170,400
Total Gastos $50,000
TOTAL EFECTIVO EN CAJA .. $474,500
GASTOS DETALLADOS
PAGO PANES HAMBURGUESA 10000
LECHE PARA COCINA 6000
PAGO DOMICILIOS 22000
SALSEROS DE 3 ONZA PARA SAL 12000
EFECTIVO REGIS. CAJERO $507,300
SOBRANTE $52,800"""
def vale(n, v): return f"SU RESTAURANTE\nGASTO DE CAJA\nConsecutivo : {n}\nResponsable: CAJA\nFecha : 15/09/2026 10:5{n - 239}:00 p. m.\nVALOR: ${v:,}\nMEDIO PAGO :\nDescripcion:\n"
VALES = [(239, 10000), (240, 6000), (241, 22000), (242, 12000)]

ok = True
def chk(c, msg):
    global ok; ok &= bool(c); print(("✓ " if c else "✗ ") + msg)

docs = leer_texto(CIERRE, "cierre")
for t in C: docs += leer_texto(comanda(t), "comandas")
for n, v in VALES: docs += leer_texto(vale(n, v), "gastos")
V = [d for d in docs if d["tipo"] == "venta"]
chk(len(V) == 21 and not any(d["avisos"] for d in V), f"21 comandas leídas, todas con pagos que cuadran con consumo + domicilio + propina")
chk(docs[0]["fecha"] == "2026-09-15", f"fecha del cierre «15-sept-26» → {docs[0]['fecha']}")
d = {x["numero"]: x for x in V}
chk(d["85621"]["efectivo"] == 35500 and d["85607"]["domicilio"] == 5000 and d["85626"]["cortesia"] == 49800 and d["85619"]["tarjeta"] == 29150,
    "efectivo con cambio (50.000 − 14.500), domicilio, cortesía y pago con tarjeta con propina")
r = construir("2026-09-15", docs, {})
cr = {x["concepto"]: x for x in r["cruces"]}
for k in ("Tarjetas (sin propina)", "Transferencias / app (con propina)", "Propinas (total)", "Propinas en efectivo", "Domicilios cobrados", "Descuentos y cortesías", "Gastos de caja"):
    chk(cr[k]["ok"], f"cruce con el cierre ✓ {k}: {cr[k]['cierre']:,}")
chk(r["faltan"] == [85610], f"detecta la comanda que falta: {r['faltan']}")
chk(cr["Venta en efectivo (sin propina)"]["diferencia"] == 24900 and cr["Venta total (sin domicilios ni propinas)"]["diferencia"] == 24900, "y la diferencia es 24.900 en la venta total y en efectivo (una comanda en efectivo)")
chk(not cr["Número de comandas"]["ok"] and "85610" in cr["Número de comandas"]["nota"], "el cierre dice 22 comandas y hay 21")
ef = [x for x in r["filas"] if x["codigo"] in ("11050501", "28150502", "28150501", "41401501") and x["tercero"] == "Consumidor Final" and x["medio"] == "Efectivo"]
chk([(x["codigo"], x["debito"], x["credito"]) for x in ef] == [("11050501", 149500, 0), ("28150502", 0, 4000), ("41401501", 0, 145500)],
    "bloque de efectivo: Efectivo 149.500 = Propinas 4.000 (solo en efectivo) + Restaurante 145.500; las propinas por transferencia/tarjeta no entran")
bco = sum(x["debito"] for x in r["filas"] if x["codigo"] == "11200501" and x["grupo"] == "venta")
tj, tr = sum(x["tarjeta"] for x in V), sum(x["transf"] for x in V)
chk(bco == tj + tr and r["diferencia"] == 0, f"sin extracto, lo pagado con tarjeta ({tj:,}) y transferencia ({tr:,}) entra al banco desde las comandas y el día cuadra")
r_b = construir("2026-09-15", docs, {"tarjetas": 300000, "nequi": 1200000})
chk(sum(x["debito"] for x in r_b["filas"] if x["codigo"] == "11200501" and x["grupo"] == "venta") == 1500000 and r_b["diferencia"] == 0,
    "con extracto (tarjetas + Nequi) manda el extracto y no se duplica lo de las comandas")
vales = [x for x in docs if x["tipo"] == "gasto_caja"]
completar_desde_cierre(docs); cl = Clasificador()
for x in vales: x["cuenta"] = cl.clasificar("", x["detalle"], x["texto"])["cuenta"]
chk({x["numero"]: x["cuenta"] for x in vales if x["cuenta"]}.get("241") == "28150501" and sum(x["valor"] for x in vales) == 50000,
    "los 4 vales suman 50.000 como el cierre; «pago domicilios» → 28150501; la descripción que no se lee se toma del cierre")
print("\n" + ("TODO OK" if ok else "HAY FALLOS"))
