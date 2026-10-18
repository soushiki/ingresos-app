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
print("\n" + ("TODO OK" if not fallos else f"{len(fallos)} FALLOS")); sys.exit(1 if fallos else 0)
