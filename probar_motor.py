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
chk(all(x.split(".")[0] in sys.stdlib_module_names or x in ("", "numeros", "puc", "asientos", "documentos") or x.startswith(".") or x.startswith("parser_module") for x in mods - {"__future__"}),
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

# T5b / ADR-023: bigramas minados, FRASES con la cuenta de mayoría, terceros persona (local), choque domiciliario «por confirmar»
r = prod.clasificar_item("gasto", "Pago de compras")
chk((r["cuenta"], r["capa"]) == ("14050501", "frase"), f"ADR-023: «Pago de compras» → mayoría del manual {r['cuenta']} ({r['capa']}, {r['motivo']})")
r = prod.clasificar_item("gasto", "propina")
chk(r["cuenta"] == "28150502" and r["capa"] != "puente", f"ADR-023: «propina» → {r['cuenta']} ({r['capa']})")
r = prod.clasificar_item("gasto", "Domcilios (Cierre)")
chk(r["capa"] == "confirmar" and "por confirmar" in r["motivo"] and r["cuenta"] == PC["decisiones"][0]["cuenta"], f"ADR-023: «Domcilios (Cierre)» → choque domiciliario por confirmar ({r['cuenta']}, {r['motivo']})")
chk(PC["decisiones"][0].get("motor") is True and PC["decisiones"][0]["estado"] == "por confirmar", "el choque 28150501/28150502 vive en por_confirmar.json «por confirmar»")
r = Motor({"lexico": {}, "bigramas": {"hacer pedido": {"cuenta": "14050501", "n": 2, "de": 2}}}, {}, {}).clasificar_item("gasto", "hacer el pedido")
chk((r["cuenta"], r["capa"]) == ("14050501", "minado") and "«hacer pedido» 2 de 2" in r["motivo"], f"bigrama minado ({r['capa']}, {r['motivo']})")
TERC = {"fulano de tal": {"cuenta": "51050601", "n": 4}}
r = Motor({}, {}, {}, TERC).clasificar_item("gasto", "cosa rara", "Fulano de Tal")
chk((r["cuenta"], r["capa"]) == ("51050601", "proveedor"), f"tercero persona (terceros_cuentas.json) → {r['cuenta']} ({r['capa']}, {r['motivo']})")
r = Motor({}, {}, {}).clasificar_item("gasto", "cosa rara", "Fulano de Tal")
chk(r["capa"] == "puente", "sin ese archivo el tercero persona no decide")
_c = Path(__file__).parent / "parser_module" / "contable"
tp = json.loads((_c / ("terceros_cuentas.json" if (_c / "terceros_cuentas.json").is_file() else "terceros_cuentas.example.json")).read_text(encoding="utf8"))
nombre = next(iter(tp)); r = prod.clasificar_item("gasto", "cosa rara", nombre)
chk(r["capa"] == "proveedor" and r["cuenta"], f"Motor.desde_archivos lee terceros_cuentas: «{nombre}» → {r['cuenta']} ({r['capa']})")

# ---------- T8 · clasificar_doc (R1, R5): el papel entero ----------
import copy, json, shutil, tempfile
mt = Motor(MODELO, {"origen": {"venta": "41401501", "rappi": "41401501", "cierre": "41401501"}}, APRENDIDO)
def item(n, v, **k): return dict(nombre=n, cant=1, valor=v, cuenta="", conf=0.0, capa="", motivo="", manual="") | k
fa = dict(tipo="factura", tercero="Proveedor Prueba", detalle="", valor=30000, texto="", items=[item("pollo", 20000), item("jabon", 10000)])
mt.clasificar_doc(fa)
chk([(i["cuenta"], i["capa"]) for i in fa["items"]] == [("14050501", "lexico"), ("51952501", "lexico")] and all(i["motivo"] for i in fa["items"]), "factura de 2 ítems: cada uno con cuenta, capa y motivo")
chk(fa["cuenta"] == "14050501" and fa["motivo"].startswith("palabras"), "doc.cuenta = la del ítem de mayor valor")
antes = copy.deepcopy(fa); mt.clasificar_doc(fa)
chk(fa == antes, "idempotente: una segunda pasada no cambia nada")
fm = dict(tipo="factura", tercero="Proveedor Prueba", valor=100, texto="", items=[item("pollo", 100, manual="51959501")])
mt.clasificar_doc(fm)
chk(fm["items"][0]["cuenta"] == "51959501" and fm["items"][0]["capa"] == "manual" and fm["cuenta"] == "51959501", "un ítem manual se respeta")
# FIX-1: cuenta elegida a mano en la tarjeta → recalcular → sigue (2 ítems y papel viejo con cuenta_manual=true)
fx = dict(tipo="factura", tercero="Proveedor Prueba", detalle="", valor=30000, texto="", items=[item("pollo", 20000), item("jabon", 10000)])
mt.clasificar_doc(fx); fx["cuenta"], fx["cuenta_manual"] = "51350501", True
mt.clasificar_doc(fx); mt.clasificar_doc(fx)
chk(fx["cuenta"] == "51350501" and all(i["manual"] == "51350501" and i["capa"] == "manual" for i in fx["items"]), "cuenta a mano + recalcular: doc.cuenta sigue y pasa a los ítems como manual")
fv = dict(tipo="gasto_caja", tercero="", detalle="Recibo 206 compra de hielo", valor=8000, texto="", cuenta="51959501", cuenta_manual=True)
mt.clasificar_doc(fv)
chk(fv["cuenta"] == "51959501" and fv["items"][0]["manual"] == "51959501" and fv["items"][0]["capa"] == "manual", "papel viejo cuenta_manual=true: su cuenta, ítem manual")
chk(all(str(x) != "True" for d in (fx, fv) for x in (d["cuenta"], *[i["cuenta"] for i in d["items"]], *[i["manual"] for i in d["items"]])), "ninguna salida del motor es «True»")
g = dict(tipo="gasto_caja", tercero="Cuantías menores", detalle="xqzw", valor=5000, texto="")
mt.clasificar_doc(g)
chk(g["items"][0]["capa"] == "puente" and g["items"][0]["cuenta"] == PUENTE_GASTO and g["cuenta"] == "", "gasto sin palabras: ítem a la puente y doc.cuenta vacía (sigue el aviso «falta cuenta»)")
g2 = dict(tipo="gasto_caja", tercero="", detalle="Recibo 206 compra de hielo", valor=8000, texto="")
mt.clasificar_doc(g2)
chk(g2["cuenta"] == "14050502" and len(g2["items"]) == 1, "gasto de caja: ítem único por el motor")
v = dict(tipo="venta", cuenta="", conf=0.0, motivo="", items=[dict(cant=1, nombre="Pollo", valor=25000)], consumo=25000)
r = dict(tipo="venta", rappi=True, cuenta="", items=[])
c = dict(tipo="cierre", cuenta="")
for d in (v, r, c): mt.clasificar_doc(d)
chk(all(d["cuenta"] == "41401501" and d["motivo"] == "origen: comanda" for d in (v, r, c)), "venta, Rappi y cierre: 41401501, «origen: comanda»")
chk(v["items"] == [dict(cant=1, nombre="Pollo", valor=25000)], "las líneas de plato de la comanda no se tocan")

# un día de septiembre sobre una COPIA del libro (nunca se escribe datos/libro.json), por la ruta real de la app (_clasificar)
COMPRAS = ("factura", "gasto_caja", "caja_menor_manuscrito")
tmp = Path(tempfile.mkdtemp(prefix="probar_motor_")); copia = tmp / "libro.json"
fuente = Path(__file__).parent / "datos" / "libro.json"
if fuente.is_file():
    shutil.copy2(fuente, copia); lib = json.loads(copia.read_text(encoding="utf8"))
    dia = max((k for k in lib if k.startswith("2026-09")), key=lambda k: len(lib[k].get("documentos", [])), default=None)
    if dia:
        import app as _app
        docs = copy.deepcopy(lib[dia]["documentos"])
        for d in docs:
            if d["tipo"] in COMPRAS: d.pop("items", None); d["cuenta"] = ""
        t0 = time.perf_counter(); _app._clasificar(docs); seg = time.perf_counter() - t0
        compras = [d for d in docs if d["tipo"] in COMPRAS]
        chk(compras and all(d["items"] and all(i["capa"] and i["motivo"] and i["cuenta"] for i in d["items"]) for d in compras),
            f"{dia}: {len(compras)} compras de {len(docs)} papeles con items[].cuenta/capa/motivo")
        chk(seg < 1, f"N3: clasificar el día {dia} ({len(docs)} papeles) en {seg:.3f} s < 1 s")
        otra = copy.deepcopy(docs); _app._clasificar(otra)
        chk(otra == docs, "el día entero es idempotente")
    else: print("(sin días de septiembre en la copia del libro: se omite)")
else: print("(sin datos/libro.json: se omite la prueba del día)")
shutil.rmtree(tmp, ignore_errors=True)

# multicuenta con un ítem a la puente: DATOS OCR y aviso del libro lo marcan (nombra papel e ítem)
from parser_module.contable.asientos import construir, FALTA_CUENTA
mp = dict(tipo="factura", id="p1", numero="F1", tercero="Proveedor Prueba", detalle="", valor=30000, medio="Efectivo", contar=True, texto="", fecha="2026-09-10", avisos=[],
          items=[item("pollo", 20000), item("xqzw", 10000)])
mt.clasificar_doc(mp)
rr = construir("2026-09-10", [mp], {}, None, None, None)
fp = [d for d in rr["datos_ocr"] if d["id"] == "p1"] if "datos_ocr" in rr else []
chk(any("falta la cuenta" in a and "F1" in a and "xqzw" in a for a in rr["avisos"]) and all((f.get("debito") or 0) >= 0 and (f.get("credito") or 0) >= 0 for f in rr["filas"]), f"ítem a la puente en papel multicuenta → aviso con papel e ítem ({[a for a in rr['avisos'] if 'cuenta' in a]})")

# 6-test · R2: los «Gastos detallados» del cierre llegan como ítem del vale sin descripción (completar_desde_cierre corre antes del motor)
from parser_module.contable import completar_desde_cierre
vale = dict(tipo="gasto_caja", tercero="Cuantías menores", detalle="", valor=8000, texto="")
cie = dict(tipo="cierre", cuenta="", gastos_detalle=[("HIELO", 8000)])
for d in completar_desde_cierre([vale, cie]): mt.clasificar_doc(d)
chk(vale["detalle"] == "Hielo" and vale["items"][0]["cuenta"] == "14050502" and vale["items"][0]["capa"] != "puente", f"R2: gasto del cierre → ítem del vale clasificado ({vale['items'][0]})")

# FIX-2 · ítems vigentes: la puente se reclasifica; si cambia el papel, los ítems no manuales se rehacen; lo manual no cambia
v2 = dict(tipo="gasto_caja", tercero="Cuantías menores", detalle="", valor=8000, texto="")
mt.clasificar_doc(v2)
chk(v2["items"][0]["capa"] == "puente" and not v2["cuenta"], "FIX-2: vale sin detalle → puente")
v2["detalle"] = "hielo"; mt.clasificar_doc(v2)
chk(v2["items"][0]["cuenta"] == "14050502" and v2["items"][0]["capa"] != "puente" and v2["cuenta"] == "14050502", f"FIX-2: llega el detalle «hielo» → 14050502 ({v2['items'][0]})")
g2 = dict(tipo="gasto_caja", tercero="Distribuidora Frutas", detalle="", valor=50000, texto="")
mt.clasificar_doc(g2); o1 = g2["items"][0]["motivo"]
g2["tipo"] = "factura"; g2["items"] = []; mt.clasificar_doc(g2)
chk(g2["items_huella"][0] == "factura" and g2["items"][0]["motivo"], f"FIX-2: gasto_caja → factura reclasifica ({o1} → {g2['items'][0]['motivo']})")
g3 = dict(tipo="gasto_caja", tercero="Distribuidora Frutas", detalle="", valor=50000, texto="")
mt.clasificar_doc(g3); g3["tipo"] = "factura"; mt.clasificar_doc(g3)
chk(g3["items"][0]["motivo"] == g2["items"][0]["motivo"], "FIX-2: cambio de tipo sin tocar los ítems → mismo resultado que rehacerlos")
g3["valor"] = 70000; mt.clasificar_doc(g3)
chk(g3["items"][0]["valor"] == 70000, "FIX-2: cambia el valor → el ítem se rehace con el valor nuevo")
m2 = dict(tipo="gasto_caja", tercero="X", detalle="hielo", valor=8000, texto="", cuenta="51350501", cuenta_manual=True)
mt.clasificar_doc(m2); m2["detalle"] = "pollo"; m2["valor"] = 9000; mt.clasificar_doc(m2)
chk(m2["items"][0]["cuenta"] == "51350501" and m2["cuenta"] == "51350501", "FIX-2: lo manual no cambia aunque cambie el papel")

print("\n" + ("TODO OK" if ok else "HAY FALLOS"))
sys.exit(0 if ok else 1)

# DEBT-2 · el MOTOR se recarga si cambia el mtime de por_confirmar.json (sin reiniciar); sin cambio no se recarga
import os, app as _app2
_pcf = _app2._CONT_DIR / "por_confirmar.json"; _st = _pcf.stat()
_m0 = _app2._motor_vigente(); chk(_app2._motor_vigente() is _m0, "DEBT-2: sin cambio de archivos el MOTOR no se recarga")
try:
    os.utime(_pcf, ns=(_st.st_atime_ns, _st.st_mtime_ns + 5_000_000_000))
    _app2._clasificar([dict(tipo="gasto_caja", tercero="X", detalle="hielo", valor=1000, texto="")])
    chk(_app2.MOTOR is not _m0 and _app2._motor_vigente() is _app2.MOTOR, "DEBT-2: cambia el mtime de por_confirmar.json → la siguiente clasificación usa un MOTOR nuevo")
finally:
    os.utime(_pcf, ns=(_st.st_atime_ns, _st.st_mtime_ns)); _app2._motor_vigente()
