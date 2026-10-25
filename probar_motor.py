"""Prueba del Motor por capas (T3, ADR-020): origen → enseñado → frase/léxico → minado/proveedor → vecino → puente.
Una prueba por capa con un modelo sintético, «domcilios» → vecino, empate → puente, y 1.000 ítems < 5 s con el modelo de producción."""
import ast, sys, time
from pathlib import Path
from parser_module.contable.clasificar import Motor, PUENTE_GASTO

ok = True
def chk(c, m):
    global ok; ok &= bool(c); print(("✓ " if c else "✗ ") + m)

MODELO = {"version": 1, "meses": ["2026-06", "2026-07"],
          "lexico": {"luz": {"cuenta": "51353001", "n": 2, "de": 2}, "parrilla": {"cuenta": "51501501", "n": 3, "de": 3}},
          "proveedores": {"distribuidora xyz s.a.s.": {"cuenta": "14050502", "n": 5, "de": 5}},
          "vecinos": [{"texto": "domicilios", "cuenta": "28150501", "fuente": "julio fila 631"},
                      {"texto": "abono local", "cuenta": "51201001", "fuente": "junio fila 40"},
                      {"texto": "abono locales", "cuenta": "13301501", "fuente": "julio fila 41"}]}
APRENDIDO = {"terceros": {"tienda don jose": "51952501"}, "detalles": {"bolsa grande": "14050503"}}
m = Motor(MODELO, {}, APRENDIDO)
CLAVES = {"cuenta", "conf", "capa", "motivo"}

r = m.clasificar_item("venta", "Hamburguesa doble")
chk(set(r) == CLAVES, f"devuelve {{cuenta, conf, capa, motivo}}: {sorted(r)}")
chk((r["cuenta"], r["capa"], r["motivo"]) == ("41401501", "origen", "origen: comanda"), f"origen: venta → 41401501 «origen: comanda» ({r['capa']})")
chk(m.clasificar_item("rappi", "Combo")["capa"] == "origen" and m.clasificar_item("cierre", "")["capa"] == "origen", "origen: rappi y cierre también")
r = m.clasificar_item("gasto", "Bolsa grande")
chk((r["cuenta"], r["capa"]) == ("14050503", "enseñado"), f"enseñado (descripción): bolsa grande → {r['cuenta']} ({r['capa']})")
r = m.clasificar_item("factura", "cosa rara", "Tienda Don José")
chk((r["cuenta"], r["capa"]) == ("51952501", "enseñado"), f"enseñado (proveedor): {r['cuenta']} ({r['capa']})")
r = m.clasificar_item("gasto", "Papel higiénico x4")
chk((r["cuenta"], r["capa"]) == ("51952501", "frase"), f"frase: papel higiénico → {r['cuenta']} ({r['capa']}, {r['motivo']})")
r = m.clasificar_item("gasto", "Transporte de compras")
chk((r["cuenta"], r["capa"]) == ("51355001", "lexico"), f"léxico a mano: transporte → {r['cuenta']} ({r['capa']})")
r = m.clasificar_item("gasto", "Pago recibo luz")
chk((r["cuenta"], r["capa"]) == ("51353001", "minado") and "2 de 2" in r["motivo"], f"léxico minado: luz → {r['cuenta']} ({r['capa']}, {r['motivo']})")
r = m.clasificar_item("factura", "articulo varios", "DISTRIBUIDORA XYZ S.A.S.")
chk((r["cuenta"], r["capa"]) == ("14050502", "proveedor"), f"proveedor minado: {r['cuenta']} ({r['capa']}, {r['motivo']})")
r = m.clasificar_item("gasto", "domcilios")
chk((r["cuenta"], r["capa"]) == ("28150501", "vecino") and "julio fila 631" in r["motivo"], f"vecino: «domcilios» → {r['cuenta']} ({r['motivo']})")
r = m.clasificar_item("gasto", "abono locale")
chk((r["cuenta"], r["capa"]) == (PUENTE_GASTO, "puente") and "empate" in r["motivo"], f"empate de vecinos (< 0,05) → puente: {r['motivo']}")
r = m.clasificar_item("gasto", "xqzw")
chk((r["cuenta"], r["capa"], r["conf"]) == (PUENTE_GASTO, "puente", 0.0), f"sin nada → puente {r['cuenta']} ({r['motivo']})")
chk(Motor(MODELO, {"puentes": {"gasto": "51959599"}}, {}).clasificar_item("gasto", "xqzw")["cuenta"] == "51959599", "la puente sale de «confirmar» si viene")
r = m.clasificar_item("gasto", "domicilio carne")          # léxico a mano empatado (28150501 vs 14050501) no decide: sigue a las capas de abajo
chk(r["capa"] != "lexico", f"empate en el léxico a mano no decide: {r['capa']} ({r['motivo']})")
chk(m.clasificar_item("gasto", "transporte", "")["conf"] >= 0.75 and m.clasificar_item("gasto", "domcilios")["conf"] >= 0.75, "conf ≥ 0,75 en léxico y vecino")

# ADR-020 fitness: solo stdlib y el paquete
fuente = (Path(__file__).parent / "parser_module" / "contable" / "clasificar.py").read_text(encoding="utf8")
mods = {(n.module or "") if isinstance(n, ast.ImportFrom) else a.name for n in ast.walk(ast.parse(fuente)) if isinstance(n, (ast.Import, ast.ImportFrom)) for a in n.names}
chk(all(x.split(".")[0] in sys.stdlib_module_names or x in ("", "numeros") or x.startswith(".") or x.startswith("parser_module") for x in mods - {"__future__"}),
    f"ADR-020: dependencia nueva en el motor ({sorted(mods)})")

# N3 / ADR-020: 1.000 ítems < 5 s con el modelo de producción
prod = Motor.desde_archivos()
base = [v["texto"] for v in prod.modelo["vecinos"]] + list(prod.modelo["lexico"]) + ["compra varios", "xqzw", "domcilios", "pago recivo luz"]
items = [(base[i % len(base)][::-1] if i % 3 == 0 else base[i % len(base)] + ("s" if i % 2 else "")) for i in range(1000)]
t = time.perf_counter(); res = [prod.clasificar_item("gasto", x) for x in items]; dt = time.perf_counter() - t
capas = {}
for x in res: capas[x["capa"]] = capas.get(x["capa"], 0) + 1
chk(dt < 5, f"ADR-020/N3: 1.000 ítems en {dt:.2f} s (< 5 s) · capas {capas}")
chk(all(set(x) == CLAVES and x["cuenta"] for x in res), "toda salida trae cuenta (o la puente) y las 4 claves")
print("\n" + ("TODO OK" if ok else "HAY FALLOS"))
sys.exit(0 if ok else 1)
