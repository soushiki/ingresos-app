"""M-13 T1 · ADR-008: marcadores de recibos faltantes (puro)."""
import sys
from parser_module.contable import faltantes as F

fallos = []
def chk(cond, msg):
    print(("✓ " if cond else "✗ ") + msg)
    if not cond: fallos.append(msg)

ms = F.crear([85388, 85391], "foto1.jpg#1", "2026-09-22", "abcdef0123456789.jpg")
chk(len(ms) == 2 and [m["numero"] for m in ms] == ["85388", "85391"], "crear desde números: un marcador por número")
m = ms[0]
chk(m["tipo"] == "faltante" and m["estado"] == "falta" and m["contar"] is False and m["recorte"] == "abcdef0123456789.jpg"
    and m["origen"] == "foto1.jpg#1" and m["fecha"] == "2026-09-22" and "85388" in m["avisos"][0], "marcador con el esquema del diseño")
chk(len({x["id"] for x in ms}) == 2, "ids distintos")
nn = F.crear([], "raro.jpg#1", "2026-09-22", None, nombre_entendido=False)
chk(len(nn) == 1 and nn[0]["numero"] == "" and nn[0]["recorte"] is None and "No entiendo el nombre" in nn[0]["avisos"][0], "nombre no entendido: un marcador sin número")

v = F.anotar(m, {"valor": 15000, "medio": "efectivo"})
chk(v["id"] == m["id"] and v["tipo"] == "venta" and v["origen"] == "manual" and v["de_foto"] == "foto1.jpg#1"
    and v["estado"] == "revisado" and v["revisado"] is True and v["valor"] == 15000 and v["numero"] == "85388", "anotar → venta manual con de_foto")
chk(m["tipo"] == "faltante", "anotar no muta el marcador")
try: F.anotar(v, {}); chk(False, "anotar una venta debe fallar")
except ValueError: chk(True, "anotar una venta normal falla")

c = F.cerrar(ms[1], "no existe, saltó el consecutivo")
chk(c["estado"] == "no_existe" and c["contar"] is False and c["motivo"].startswith("no existe"), "cerrar → no_existe con motivo")
chk(F.cerrar(ms[1], "x" * 200)["motivo"] == "x" * 200, "motivo de 200 pasa")
try: F.cerrar(ms[1], "x" * 201); chk(False, "motivo 201 debe fallar")
except ValueError: chk(True, "motivo > 200 falla")
try: F.cerrar(c, "otra vez"); chk(False, "cerrar uno cerrado debe fallar")
except ValueError: chk(True, "cerrar un marcador ya cerrado falla")

chk(F.abiertos([m, c, v, {"tipo": "venta"}]) == [m], "abiertos: solo faltantes en estado falta")

previos = [v, c]
nuevos = F.crear([85388, 85391, 85400], "foto1.jpg#1", "2026-09-22", None)
r = F.reconciliar(previos, nuevos)
chk([x["numero"] for x in r] == ["85400"], "reconciliar: anotado y no_existe no vuelven, abierto sí")
otra = F.crear([85388], "foto2.jpg#1", "2026-09-22", None)
chk(F.reconciliar(previos, otra) == otra, "reconciliar: misma numeración en otra foto sí vuelve")
chk(F.reconciliar([], nuevos) == nuevos, "reconciliar sin previos no quita nada")

print("OK" if not fallos else f"FALLÓ {len(fallos)}")
sys.exit(1 if fallos else 0)
