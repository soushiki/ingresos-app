"""T3 · R1: validar(doc, ctx) puro. Un caso que pasa y uno por cada motivo, con el texto exacto."""
import sys
from parser_module.contable.validar import validar

fallos = []
def chk(cond, msg):
    print(("✓ " if cond else "✗ ") + msg)
    if not cond: fallos.append(msg)

def doc(**kw):
    d = dict(tipo="venta", numero="85560", hora="20:01", detalle="Mesa M2 · Mesero Yorlin", medio="Efectivo",
             items=[dict(cant=1, nombre="PLATO", valor=40000), dict(cant=1, nombre="JUGO", valor=10000)], subtotal=50000, descuento=5000,
             consumo=45000, domicilio=2000, propina=4500, pagado=60000, cambio=8500, efectivo=43000 + 0, tarjeta=0, transf=0, credito=0)
    d["efectivo"] = 51500; d.update(kw); return d

chk(validar(doc()) == [], "recibo cuadrado: sin motivos")
chk(validar(doc(numero="")) == ["Falta el número de recibo"], "falta número")
chk(validar(doc(hora="")) == ["Falta la hora"], "falta hora")
chk(validar(doc(detalle="Mesero Yorlin")) == ["Falta la mesa"], "falta mesa")
chk(validar(doc(medio="")) == ["Falta el medio de pago"], "falta medio")
chk(validar(doc(subtotal=60000, descuento=15000)) == ["Los ítems suman 50.000 y el subtotal dice 60.000"], "ítems ≠ subtotal")
chk(validar(doc(subtotal=60000, descuento=15000), {"regla_items": False}) == [], "regla de ítems apagada por config")
chk(validar(doc(descuento=0)) == ["Subtotal 50.000 − descuento 0 no da el consumo 45.000"], "subtotal − descuento ≠ consumo")
chk(validar(doc(propina=0, efectivo=47000, cambio=13000)) == [], "otra combinación cuadrada")
chk(validar(doc(propina=1000)) == ["Pagado 60.000 − cambio 8.500 no da consumo + domicilio + propina (48.000)"], "pagado − cambio ≠ consumo+domicilio+propina")
chk(validar(doc(efectivo=40000)) == ["Los medios de pago suman 40.000 y pagado − cambio es 51.500"], "medios ≠ pagado − cambio")
chk(validar(doc(cambio=8000)) == ["Pagado 60.000 − cambio 8.000 no da consumo + domicilio + propina (51.500)",
                                  "Los medios de pago suman 51.500 y pagado − cambio es 52.000"], "dos motivos a la vez")
chk(validar(doc(subtotal=50050), {"tolerancia": 100}) == [], "la tolerancia de config absorbe 50 pesos")
chk(validar(doc(subtotal=50050, descuento=5050)) != [], "tolerancia 0 por defecto")
chk(validar(doc(cortesia=45000, consumo=0, subtotal=45000, pagado=0, cambio=0, efectivo=0)) == [], "cortesía: no se exige aritmética")
chk(validar(doc(tipo="gasto_caja", numero="", hora="")) == [], "solo valida ventas")

# T8 · R5: el nombre de la foto dice qué recibos trae; los vecinos no deben tener los mismos montos con otra mesa u hora
from parser_module.contable.validar import numeros_de_nombre, rango_de_nombre, faltantes, cruces, FALTA
chk(rango_de_nombre("85560 al 565") == (85560, 85565), "«85560 al 565» → (85560, 85565)")
chk(numeros_de_nombre("2/comandas/85310 al 315.jpg#1") == list(range(85310, 85316)), "carpeta, extensión y «#página» no estorban")
chk(numeros_de_nombre("5/comandas/85413 al 415 y 417 al 419.jpg") == [85413, 85414, 85415, 85417, 85418, 85419], "dos rangos con «y»")
chk(numeros_de_nombre("85316-317-321.jpg") == [85316, 85317, 85321], "lista con guiones abreviada")
chk(numeros_de_nombre("85319-318-rappi.jpg") == [85318, 85319], "«rappi» y orden suelto")
chk(numeros_de_nombre("x\\comandas20260916_85627-628-629.pdf#1") == [85627, 85628, 85629], "prefijo comandasAAAAMMDD_ y ruta de Windows")
chk(numeros_de_nombre("85998 al 002") == list(range(85998, 86003)), "rango que cruza el millar")
for raro in ("85334-338 al 3341-343.jpg", "comandas20261002_15304850.pdf", "IMG_20260916_123456.jpg", "rappi.jpg", "85560 al", "85560 al 85500"):
    chk(numeros_de_nombre(raro) is None, f"nombre raro sin R5: {raro}")
chk(validar(doc(), {"esperados": [85560, 85561]}) == [], "número dentro del nombre")
chk(validar(doc(numero="85568"), {"rango": (85560, 85565)}) == ["El recibo 85568 no está en el nombre de la foto (85560 al 85565)"], "número fuera del rango")
chk(validar(doc(numero="85568"), {"esperados": [85560, 85562, 85563, 85564]}) == ["El recibo 85568 no está en el nombre de la foto (85560, 85562 al 85564)"], "fuera de la lista, texto compacto")
chk(faltantes([doc(numero="85560"), doc(numero="85562"), dict(tipo="gasto_caja", numero="85561")], [85560, 85561, 85562]) == [85561], "falta un número (el gasto no cuenta)")
chk(FALTA.format(85563) == "Falta el recibo 85563 en esta foto", "texto del aviso de faltante")
a, b = doc(), doc(numero="85561", detalle="Mesa M5 · Mesero Yorlin")
chk(cruces(a, [a, b]) == ["Mismos montos que el recibo 85561 con distinta mesa u hora: posible cruce de valores"], "montos idénticos con otra mesa")
chk(validar(a, {"vecinos": [a, doc(numero="85561", hora="21:15")]}) == ["Mismos montos que el recibo 85561 con distinta mesa u hora: posible cruce de valores"], "montos idénticos con otra hora, por ctx")
chk(cruces(a, [doc(numero="85561")]) == [], "misma mesa y hora: no es cruce")
chk(cruces(a, [doc(numero="85561", detalle="Mesa M5", cambio=500, pagado=52000)]) == [], "solo el consumo igual (otro pago): no es cruce")
print("\n" + ("TODO OK" if not fallos else f"{len(fallos)} FALLOS")); sys.exit(1 if fallos else 0)
