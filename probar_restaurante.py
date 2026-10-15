"""Prueba de la plantilla «Restaurante · ganancias y pérdidas» con cierres de caja escritos de formas MUY distintas.
    python probar_restaurante.py"""
from pathlib import Path
from parser_module import Config, Esquema, parsear

ESQ = Esquema.plantilla("restaurante_pyg")
CASOS = [
    # (descripción, texto del OCR, {columna: valor esperado}, columnas que deben quedar «revisar»)
    ("FALTANTE sin signo → negativo", "FALTANTE 138.950", {"faltante_sobrante": -138950, "resultado": -138950}, []),
    ("FALTANTE con signo -$ (como el recibo)", "FALTANTE   -$138,950", {"faltante_sobrante": -138950}, []),
    ("Sobrante de caja → positivo", "Sobrante de caja: $20.000", {"faltante_sobrante": 20000}, []),
    ("PÉRDIDA DEL DÍA sin signo → negativo", "PÉRDIDA DEL DÍA: 85.000", {"resultado_impreso": -85000, "resultado": -85000}, []),
    ("Utilidad neta → positivo", "Utilidad neta 120.000", {"resultado_impreso": 120000, "resultado": 120000}, []),
    ("Ganancia/Pérdida con signo impreso", "Ganancia/Pérdida: -45.000", {"resultado_impreso": -45000}, []),
    ("Resultado del día (tal como viene)", "Resultado del día: 300.000", {"resultado_impreso": 300000}, []),
    ("Diferencia de caja con signo", "Diferencia de caja -12.000", {"faltante_sobrante": -12000}, []),
    ("Descuadre sin signo → pide revisar", "Descuadre 5.000", {"faltante_sobrante": 5000}, ["faltante_sobrante"]),
    ("Sobra o falta con signo", "Sobra o falta: -3.000", {"faltante_sobrante": -3000}, []),
    ("Etiqueta y valor en líneas separadas", "FALTANTE\n-$138,950", {"faltante_sobrante": -138950}, []),
    ("Error de lectura «Faltanre»", "Faltanre 20.000", {"faltante_sobrante": -20000}, []),
    ("Valor antes de la etiqueta", "45.000 pérdida", {"resultado_impreso": -45000}, []),
    ("Tarjeta crédito + débito (partes)", "Tarjeta crédito 500.000\nTarjeta débito 50.000", {"venta_tarjeta": 550000}, ["venta_tarjeta"]),
    ("Total tarjetas manda sobre las partes", "Total tarjetas 538.000\nCrédito 500.000\nDébito 38.000", {"venta_tarjeta": 538000}, []),
    ("La tabla «TOTAL VENTA» por hora no contamina", "5:00 p. m.\nTOTAL VENTA $52,000\n6:00 p. m.\nTOTAL VENTA $175,250", {"ventas_dia": 0}, []),
    ("Ventas totales impresas", "VENTAS TOTALES 1.300.000", {"ventas_impresas": 1300000, "ventas_dia": 1300000}, []),
    ("Resultado calculado: ventas − gastos − faltante", "Ventas totales 2.000.000\nGastos 150.000\nFaltante 30.000", {"resultado": 1820000}, []),
    ("Resultado calculado con sobrante", "Ventas totales 1.000.000\nGastos 100.000\nSobrante 5.000", {"resultado": 905000}, []),
    ("Resultado calculado desde medios de pago", "Efectivo ventas 400.000\nTotal tarjetas 300.000\nNequi 100.000\nTotal gastos 50.000\nPago a domiciliarios 20.000",
     {"ventas_dia": 800000, "resultado": 730000}, []),
    ("El resultado impreso manda sobre el calculado", "Ventas totales 1.000.000\nUtilidad 250.000", {"resultado": 250000}, []),
]
fallos = 0
for desc, texto, esp, rev in CASOS:
    c = parsear(texto, Config(esquema=ESQ), anio=2026)
    vals = {k: (c.campos[k].valor or 0) for k in ESQ.claves if ESQ.tipos[k] != "calculo"}
    todo = ESQ.evaluar(vals)
    mal = [f"{k}: {round(todo[k]) if k in todo else None} ≠ {v}" for k, v in esp.items() if round(todo.get(k, 0)) != v]
    mal += [f"{k} debía quedar «revisar»" for k in rev if c.campos[k].estado == "ok"]
    mal += [f"{k} no debía quedar «revisar» ({'; '.join(c.campos[k].razones)})" for k in esp if k in c.campos and k not in rev and c.campos[k].estado == "revisar"]
    print(("✓ " if not mal else "✗ ") + desc + ("" if not mal else "\n    " + "\n    ".join(mal)))
    fallos += bool(mal)
c = parsear(Path("parser_module/ejemplos_pos/recibo_foto3.txt").read_text(encoding="utf8"), Config(esquema=ESQ), anio=2026)
vals = {k: (c.campos[k].valor or 0) for k in ESQ.claves if ESQ.tipos[k] != "calculo"}; todo = ESQ.evaluar(vals)
ok = round(todo["ventas_dia"]) == 1243750 and round(todo["resultado"]) == 1076800 and c.campos["faltante_sobrante"].valor == -138950 and not ESQ.controlar(vals)
print(("✓ " if ok else "✗ ") + f"Recibo de referencia: ventas {todo['ventas_dia']:,.0f} · ganancia/pérdida {todo['resultado']:,.0f}"); fallos += not ok
print("\n" + ("TODO OK" if not fallos else f"{fallos} FALLOS"))
