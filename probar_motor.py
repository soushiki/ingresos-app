"""Prueba del Motor por capas (T3, ADR-020): origen → enseñado → frase/léxico → minado/proveedor → vecino → puente.
Una prueba por capa con un modelo sintético, «domcilios» → vecino, empate → puente, y 1.000 ítems < 5 s con el modelo de producción."""
import ast, re, sys, time
from pathlib import Path
from parser_module.contable.clasificar import Motor, PUENTE_GASTO, LEXICO, FRASES

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
chk(all(x.split(".")[0] in sys.stdlib_module_names or x in ("", "numeros", "puc", "asientos") or x.startswith(".") or x.startswith("parser_module") for x in mods - {"__future__"}),
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
# T4 / ADR-022: por_confirmar.json, alias y puc_valida dentro del motor
import json
from parser_module.contable import puc
PC = json.loads((Path(__file__).parent / "parser_module" / "contable" / "por_confirmar.json").read_text(encoding="utf8"))
chk(len(PC["decisiones"]) == 8 and all(d.get("estado") in ("por confirmar", "confirmado") and d.get("fuente") for d in PC["decisiones"]), "ADR-022: decisión sin estado o sin fuente (8 decisiones)")
chk({"gasto", "ingreso"} <= set(PC["puentes"]) and {"vecino", "empate", "candidatos"} <= set(PC["umbrales"]), "puentes y umbrales en por_confirmar.json")
chk(all(puc.revisar(v)[0] in ("ok", "propia") for v in PC["alias"].values()), "los destinos de los alias son válidos en el PUC")
mc = Motor(MODELO, PC, {"terceros": {}, "detalles": {"recibo gas": "51353002", "cosa xy": "99999999"}})
r = mc.clasificar_item("gasto", "Recibo gas")
chk((r["cuenta"], r["capa"]) == ("51355501", "enseñado") and "por confirmar" in r["motivo"], f"alias: 51353002 → 51355501 marcado por confirmar ({r['motivo']})")
r = mc.clasificar_item("gasto", "Cosa XY")
chk((r["cuenta"], r["capa"]) == (PUENTE_GASTO, "puente") and "fuera del PUC" in r["motivo"], f"cuenta fuera del PUC → puente ({r['motivo']})")
r = mc.clasificar_item("gasto", "Pago gas natural")
chk(r["cuenta"] == "51355501" and "por confirmar" in r["motivo"], f"frase «gas natural» (51353002) sale por alias: {r['cuenta']}")
r = Motor({"lexico": {"cachivache": {"cuenta": "51957501", "n": 3, "de": 3}}, "proveedores": {}, "vecinos": []}, PC, {}).clasificar_item("gasto", "cachivache")
chk((r["cuenta"], r["capa"]) == ("51959502", "minado") and "por confirmar" in r["motivo"], f"minado: el alias reescribe el código viejo del manual 51957501 → {r['cuenta']} ({r['motivo']})")
r = Motor({"lexico": {"honorario": {"cuenta": "51104002", "n": 3, "de": 3}}, "proveedores": {}, "vecinos": []}, PC, {}).clasificar_item("gasto", "honorario")
chk((r["cuenta"], r["capa"]) == (PUENTE_GASTO, "puente") and "51104002 fuera del PUC" in r["motivo"], f"minado fuera del PUC sin alias → puente ({r['motivo']})")
r = mc.clasificar_item("gasto", "Cosa XY", manual="51957501")
chk((r["cuenta"], r["capa"]) == ("51957501", "manual") and "aviso PUC" in r["motivo"], f"manual: no cambia la cuenta, solo avisa ({r['motivo']})")
r = mc.clasificar_item("gasto", "Cosa XY", manual="99999999")
chk((r["cuenta"], r["capa"]) == ("99999999", "manual") and "aviso PUC" in r["motivo"], f"manual fuera del PUC: se respeta y se avisa ({r['motivo']})")
chk(all(n.get("estado") in ("por confirmar", "confirmado") and n.get("fuente") for n in (PC["alias_nota"].get(k) or {} for k in PC["alias"])), "ADR-022: alias sin estado o sin fuente")
chk(all(PC["alias_nota"][k]["estado"] == "por confirmar" for k in ("51353003", "51957501", "51157501")), "alias que el ADR no nombra (internet, herramientas, 4x1000) siguen «por confirmar»")
chk(PUENTE_GASTO == PC["puentes"]["gasto"] and mc.clasificar_item("venta", "x")["cuenta"] == PC["origen"]["venta"], "puente y origen salen de la configuración")

# ADR-022 fitness (aquí y no en probar_clasificacion.py): toda salida sin `manual` es ok/propia o la puente
VALE = lambda x: x["cuenta"] == mc.puente if x["capa"] == "puente" else puc.revisar(x["cuenta"])[0] in ("ok", "propia")
malas = sorted({x["cuenta"] for x in res if not VALE(x)})
chk(not malas, f"ADR-022: cuenta fuera del PUC (1.000 ítems) {malas}")
MP = prod.modelo
cuentas = ({e["cuenta"] for e in MP["lexico"].values()} | {e["cuenta"] for e in MP["proveedores"].values()} | {v["cuenta"] for v in MP["vecinos"]}
           | set(LEXICO) | set(FRASES.values()) | set(PC["alias"]))
salidas = []
for c in sorted(cuentas):
    salidas.append(Motor({"lexico": {"zzqw": {"cuenta": c, "n": 1, "de": 1}}}, PC, {}).clasificar_item("gasto", "zzqw"))                 # minado
    salidas.append(Motor({"proveedores": {"prov zzqw": {"cuenta": c, "n": 1, "de": 1}}}, PC, {}).clasificar_item("gasto", "", "Prov ZZQW"))  # proveedor
    salidas.append(Motor({"vecinos": [{"texto": "zzqw qq", "cuenta": c, "fuente": "x"}]}, PC, {}).clasificar_item("gasto", "zzqw qq"))   # vecino
    salidas.append(Motor({}, PC, {"detalles": {"zzqw": c}}).clasificar_item("gasto", "zzqw"))                                              # enseñado
malas = sorted({(x["capa"], x["cuenta"]) for x in salidas if not VALE(x)})
capas_t = {x["capa"] for x in salidas}
chk(not malas and len(salidas) == 4 * len(cuentas), f"ADR-022: cuenta fuera del PUC ({len(cuentas)} cuentas reales × 4 capas, salen {sorted(capas_t)}) {malas}")
chk(all(d.get("estado") in ("por confirmar", "confirmado") and d.get("fuente") for d in PC["decisiones"]), "ADR-022: decisión sin estado o sin fuente")
arbol = ast.parse(fuente)
permitidos = set()
for n in ast.walk(arbol):
    if isinstance(n, (ast.Assign, ast.AugAssign)):
        ts = n.targets if isinstance(n, ast.Assign) else [n.target]
        if any((t.id if isinstance(t, ast.Name) else getattr(t.value, "id", "")) in ("LEXICO", "FRASES") for t in ts if isinstance(t, (ast.Name, ast.Subscript))):
            permitidos |= {id(k) for k in ast.walk(n)}
escondidos = [k.value for k in ast.walk(arbol) if isinstance(k, ast.Constant) and isinstance(k.value, str) and re.search(r"\b\d{8}\b", k.value) and id(k) not in permitidos]
escondidos += re.findall(r"#.*?\b(\d{8})\b", fuente)
chk(not escondidos, f"ADR-022: decisión contable escondida en el código {escondidos}")

print("\n" + ("TODO OK" if ok else "HAY FALLOS"))
sys.exit(0 if ok else 1)
