"""Prueba del esquema de columnas definido por el usuario."""
import json, tempfile, os
from parser_module import Config, Esquema, parsear

fallos = []
def chk(cond, msg):
    print(("✓ " if cond else "✗ ") + msg)
    if not cond: fallos.append(msg)

# 1) columnas propias (número y nombres libres)
esq = Esquema.desde_lista([
    {"nombre": "Total vendido"}, {"nombre": "Efectivo"}, {"nombre": "Bonificaciones"},
    {"nombre": "Gaseosas vendidas", "tipo": "conteo", "sinonimos": "gaseosa, cocas"},
    {"nombre": "Nequi"}, {"nombre": "Daviplata"}])
chk(esq.claves == ["total", "efectivo", "bonificaciones", "gaseosas_vendidas", "nequi", "daviplata"], f"claves: {esq.claves}")
cfg = Config(esquema=esq)
c = parsear("""Fecha 3/10/2026
Total vendido: 1.500.000
Efectivo 900.000
Bonificaciones: 35.000
Gaseosa 48
Nequi 400.000
Daviplata 150.000
Propinas 20.000
""", cfg, anio=2026)
chk(c.orden == esq.claves and len(c.campos) == 6, "el parser genera exactamente las 6 columnas definidas")
for k, v in {"total": 1500000, "efectivo": 900000, "bonificaciones": 35000, "gaseosas_vendidas": 48, "nequi": 400000, "daviplata": 150000}.items():
    chk(c.campos[k].valor == v, f"{c.nombres[k]} = {c.campos[k].valor} (esperado {v})")
chk(any(d["etiqueta"] == "propinas" and d["valor"] == 20000 for d in c.desconocidas), "«Propinas» (no es columna) queda como etiqueta no reconocida")
chk(list(c.a_fila()) == ["Total vendido", "Efectivo", "Bonificaciones", "Gaseosas vendidas", "Nequi", "Daviplata"], "a_fila usa los nombres del usuario")

# 2) una sola columna / reutiliza vocabulario original si el nombre coincide
e1 = Esquema.desde_lista([{"nombre": "Efec"}, {"nombre": "Domi"}])
chk(e1.claves == ["efectivo", "domicilio"], f"«Efec»/«Domi» reutilizan el vocabulario base: {e1.claves}")
c1 = parsear("Efectivo: 500.000\nDomicilios 70.000\nRappi 10.000", Config(esquema=e1))
chk(c1.campos["efectivo"].valor == 500000 and c1.campos["domicilio"].valor == 70000 and len(c1.campos) == 2, "2 columnas → 2 campos")

# 3) validaciones con mensajes claros
for nombre, lista, frag in [
    ("sin columnas", [], "al menos una"),
    ("nombre vacío", [{"nombre": " "}], "sin nombre"),
    ("nombre repetido", [{"nombre": "Base"}, {"nombre": "base"}], "se llaman"),
    ("sinónimo repetido", [{"nombre": "A1", "sinonimos": "xx"}, {"nombre": "B1", "sinonimos": "xx"}], "repetido"),
    ("demasiadas", [{"nombre": f"C{i}"} for i in range(41)], "Máximo")]:
    try: Esquema.desde_lista(lista); chk(False, f"debía fallar: {nombre}")
    except ValueError as e: chk(frag in str(e), f"{nombre} → «{e}»")

# 4) guardar/cargar y que la clave sobreviva al renombrar
d = tempfile.mkdtemp(); ruta = os.path.join(d, "esquema.json")
esq.guardar(ruta)
lista = Esquema.cargar(ruta).to_list(); lista[2]["nombre"] = "Bonos"
e2 = Esquema.desde_lista(lista)
chk(e2.claves == esq.claves and e2.nombres["bonificaciones"] == "Bonos", "renombrar conserva la clave (los datos guardados siguen válidos)")
chk(Esquema.cargar(os.path.join(d, "no_existe.json")).claves[0] == "total", "sin archivo → 12 columnas originales")

# 5) aprendizaje con columnas propias
ra = os.path.join(d, "alias.json"); cfg2 = Config.cargar(ra, esq)
cfg2.aprender("propina", "bonificaciones")
c2 = parsear("Propina 12.000", Config.cargar(ra, esq))
chk(c2.campos["bonificaciones"].valor == 12000, "una etiqueta enseñada se asigna a la columna propia")
try: cfg2.aprender("x", "no_existe"); chk(False, "debía rechazar columna inexistente")
except ValueError: chk(True, "rechaza columna inexistente")
chk(Config.cargar(ra, Esquema.defecto()).aliases["efectivo"] is not None, "al cambiar de esquema se ignoran alias de columnas que ya no existen")
print("\n" + ("TODO OK" if not fallos else f"{len(fallos)} FALLOS"))
