"""T6 (M-27, R2): items_de(doc) — ítems de factura (tabla o «nombre … valor»), ítem único si no hay o no cuadran, migración al leer."""
from parser_module.contable.documentos import items_de, parse_factura
ok = True
def chk(c, m):
    global ok; ok &= bool(c); print(("✓ " if c else "✗ ") + m)

# Textos reales de sept. (libro.json; T1: solo 3 de 96 cuadran con el total ±1 %)
T_NV = "CANT DESCIPCIÓN VR.UNIT VR.TOTAL\n1 Platahuel 7200\n1 Coca cola 6000\n1 Agua fría 7200\n1 Sabor lu 800\nTOTAL 21200\nRECIB:\nSIN TEXTO"
T_TAB = "CLIENTE: tienda y terraza | 18 9 26\nCANT | DESCRIPCIÓN | VR.UNIT | VR.TOTAL\n3 | ischugai | 9500 | 9500\n\nReci: | 1 | 1\n\nTOTAL -> 9500"
T_REF = ("DESECHABLES EL ORIENTE CTG\nNIT: 900000000|Régimen ordinario No\nREMISIÓN DE VENTA\nNo. PPAL-9706\nDESCRIPCIÓN | CANTIDAD | TOTAL\n•BOLSA KRAFT\n"
         "Ref: 00105 | 1x($22.000) | 22,000\nSUBTOTAL | $18,487\n+ Impuestos | $3,513\nTOTAL NETO | $22,000\n")
T_NOCUADRA = "Papeleria Sol S.A.S\nFactura No. A1234\n1 Resma carta 12000\n1 Lapiceros 3000\nTOTAL 40000"

def doc(texto, **kw):
    d = parse_factura(texto); d.update(kw); return d

# nombre … valor, cuadra con el total
d = doc(T_NV); its = items_de(d)
chk(d["valor"] == 21200, f"total leído 21200 ({d['valor']})")
chk([i["nombre"] for i in its] == ["Platahuel", "Coca cola", "Agua fría", "Sabor lu"] and sum(i["valor"] for i in its) == 21200, f"4 ítems que suman el total: {[(i['nombre'], i['valor']) for i in its]}")
chk(all({"nombre", "cant", "valor", "cuenta", "conf", "capa", "motivo", "manual"} <= set(i) for i in its), "cada ítem trae la forma del diseño (nombre, cant, valor, cuenta, conf, capa, motivo, manual)")
# tabla con «|»; la fila «Reci: | 1 | 1» no es ítem; «TOTAL -> 9500» se lee
d = doc(T_TAB); its = items_de(d)
chk(d["valor"] == 9500, f"«TOTAL -> 9500» se lee como total ({d['valor']})")
chk(len(its) == 1 and its[0]["nombre"] == "ischugai" and its[0]["valor"] == 9500, f"tabla: un ítem, sin el «Reci:» ({[(i['nombre'], i['valor']) for i in its]})")
# ítem que no es mercancía (Ref: …) pero cuadra → cuenta; el proveedor viaja con el ítem único
d = doc(T_REF); its = items_de(d)
chk(len(its) == 1 and its[0]["valor"] == 22000, "remisión: un ítem de 22.000 = total")
# no cuadran ±1 % → ítem único con el total y el proveedor (decisión de T1)
d = doc(T_NOCUADRA); its = items_de(d)
chk(len(its) == 1 and its[0]["valor"] == 40000 and d["tercero"].lower().startswith("papeleria"), f"no cuadra → ítem único por el total: {[(i['nombre'], i['valor']) for i in its]}")
chk("papeleria" in its[0]["nombre"].lower() or its[0].get("tercero", "").lower().startswith("papeleria"), "el ítem único lleva detalle + proveedor para el motor")
# sin ítems / sin texto
d = doc("", tipo="factura", tercero="Proveedor X", detalle="Factura 77", valor=5000)
its = items_de(d)
chk(len(its) == 1 and its[0]["valor"] == 5000 and "Proveedor X" in its[0]["nombre"] and "Factura 77" in its[0]["nombre"], "sin texto → un ítem detalle + proveedor")
# gasto de caja, venta: ítem único (los ítems de la comanda no se reparten)
g = dict(tipo="gasto_caja", detalle="Recibo 206 compra de hielo", tercero="Cuantías menores", valor=8000, texto="")
chk(items_de(g)[0]["valor"] == 8000 and len(items_de(g)) == 1, "gasto de caja → ítem único con el valor")
v = dict(tipo="venta", detalle="Mesa 3", tercero="Consumidor Final", consumo=50000, valor=0, texto="| Pollo | 1 | 25.000 |\n| Jugo | 2 | 25.000 |")
chk(len(items_de(v)) == 1 and items_de(v)[0]["valor"] == 50000, "venta → ítem único por el consumo (origen comanda, T8)")
# migración al leer
viejo = dict(tipo="factura", detalle="x", tercero="P", valor=100, cuenta="51959501", cuenta_manual="14050501", texto="")
its = items_de(viejo)
chk(its[0]["cuenta"] == "51959501" and its[0]["manual"] == "14050501", "papel viejo: ítem único con cuenta del papel y manual = cuenta_manual")
sin = dict(viejo); sin.pop("cuenta_manual")
chk(items_de(sin)[0]["manual"] == "" and items_de(sin)[0]["cuenta"] == "51959501", "papel viejo sin cuenta_manual → manual vacío")
guardado = dict(viejo, items=[dict(nombre="a", cant=1, valor=60, cuenta="14050501", conf=.9, capa="lexico", motivo="m", manual=""), dict(nombre="b", cant=1, valor=40, cuenta="51959501", conf=.5, capa="puente", motivo="", manual="")])
chk(items_de(guardado) == guardado["items"], "si ya trae items[].cuenta se devuelven tal cual (idempotente)")
# no muta el papel
d = doc(T_NV); antes = repr(d); items_de(d)
chk(repr(d) == antes, "items_de no modifica el papel")
print("\nOK" if ok else "\nFALLÓ"); raise SystemExit(0 if ok else 1)
