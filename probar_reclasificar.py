"""T10 (M-27, R7, ADR-021): reclasificar.plan / aplicar / guardar — idempotente, huella vieja falla, manual intacto, sept. < 30 s."""
import copy, json, tempfile, time
from pathlib import Path
from parser_module.contable.clasificar import Motor
from parser_module.contable.asientos import CFG
from parser_module.contable.reclasificar import plan, aplicar, guardar, HuellaDistinta, VERSION
ok = True
def chk(c, m):
    global ok; ok &= bool(c); print(("✓ " if c else "✗ ") + m)

m = Motor({}, {}, {})          # solo LEXICO/FRASES: resultado fijo
cfg = {"puente_ingreso": CFG["puente_ingreso"], "puente_gasto": CFG["puente_gasto"]}
BASE = dict(avisos=[], cliente="", conf=0.0, consumo=0, contar=True, cortesia=0, credito=0, cuenta="", descuento=0, detalle="", domicilio=0, dup_de="", efectivo=0,
            medio="Efectivo", medio_transf="", motivo="", numero="", origen="", propina=0, tarjeta=0, transf=0, tercero="", texto="", valor=0)
def papel(id, tipo, **kw): return dict(BASE, id=id, tipo=tipo, fecha="2026-09-05", origen=f"5/gastos/{id}.jpg#1", **kw)

viejo = papel("g1", "gasto_caja", numero="11", detalle="Hielo", valor=8000, cuenta="51355001")                 # papel viejo sin ítems, cuenta equivocada
a_mano = papel("g2", "gasto_caja", numero="12", detalle="Cerveza", valor=50000, cuenta="51952501", cuenta_manual=True)   # el usuario eligió 51952501
fac = papel("f1", "factura", numero="F9", tercero="Distribuidora", valor=30000,
            items=[dict(nombre="Cerveza", cant=1, valor=20000, cuenta="51952501", conf=0.9, capa="lexico", motivo="x", manual=""),
                   dict(nombre="Escoba", cant=1, valor=10000, cuenta="13452501", conf=1.0, capa="manual", motivo="lo pusiste a mano", manual="13452501")])
venta = papel("v1", "venta", numero="900", consumo=40000, efectivo=40000)
LIB = {"2026-09-05": dict(fecha="2026-09-05", documentos=[viejo, a_mano, fac, venta], banco={}, cierre={}, cruces=[], filas=[], pendientes=[], debito=0, credito=0,
                          diferencia=0, guardado="2026-09-06T10:00:00"),
       "2026-08-31": dict(fecha="2026-08-31", documentos=[papel("g9", "gasto_caja", detalle="Hielo", valor=1000, cuenta="51355001")], banco={}, cierre={}, guardado="x")}
foto = json.dumps(LIB, sort_keys=True)

p = plan(LIB, "2026-09", m)
chk(json.dumps(LIB, sort_keys=True) == foto, "plan no toca el libro")
por = {(c["doc_id"], c["item"]): c for c in p["cambios"]}
chk(set(por) == {("g1", "Hielo"), ("f1", "Cerveza")}, f"cambia el papel viejo y el ítem no manual: {sorted(por)}")
chk(por.get(("g1", "Hielo"), {}).get("despues") == "14050502" and por[("g1", "Hielo")]["antes"] == "51355001", "papel viejo: 51355001 → 14050502 (hielo)")
chk(por.get(("f1", "Cerveza"), {}).get("despues") == "14050502", "ítem no manual de la factura se reclasifica (51952501 → 14050502)")
chk(not any(c["doc_id"] == "g2" or c["item"] == "Escoba" for c in p["cambios"]), "lo manual no sale en el plan (S2)")
chk(all(c["fecha"].startswith("2026-09") for c in p["cambios"]), "solo el mes pedido (agosto queda)")
chk(not any(c["tipo"] == "venta" for c in p["cambios"]), "ventas no se reclasifican (origen)")
chk(p["resumen"].get("51355001") == {"antes": 8000, "despues": 0} and p["resumen"]["14050502"]["despues"] == 28000, f"resumen por cuenta: {p['resumen']}")
chk(len(p["huella"]) == 64 and p["huella"] == plan(LIB, "2026-09", m)["huella"], "huella sha256 estable")

# huella alterada o libro cambiado → no aplica
try: aplicar(LIB, dict(p, huella="0" * 64), m, cfg); chk(False, "ADR-021: se aplicó un plan distinto a la vista previa")
except HuellaDistinta: chk(json.dumps(LIB, sort_keys=True) == foto, "huella alterada → HuellaDistinta y el libro intacto")
otro = copy.deepcopy(LIB); otro["2026-09-05"]["guardado"] = "2026-09-07T08:00:00"
try: aplicar(otro, p, m, cfg); chk(False, "ADR-021: se aplicó un plan distinto a la vista previa (día guardado después)")
except HuellaDistinta: chk(True, "día guardado entre plan y aplicar → HuellaDistinta")
try: aplicar(LIB, dict(p, mes=""), m, cfg); chk(False, "sin mes no aplica")
except HuellaDistinta: chk(True, "vista sin mes → HuellaDistinta")

nuevo = aplicar(LIB, p, m, cfg, ahora="2026-10-25T12:00:00")
chk(json.dumps(LIB, sort_keys=True) == foto, "aplicar no muta el libro de entrada")
dia = nuevo["2026-09-05"]; docs = {d["id"]: d for d in dia["documentos"]}
chk(docs["g2"]["items"][0]["cuenta"] == "51952501" and docs["g2"]["cuenta"] == "51952501", "ADR-021: se pisó una corrección manual" if docs["g2"]["cuenta"] != "51952501" else "cuenta a mano del papel sigue en 51952501")
esc = next(i for i in docs["f1"]["items"] if i["nombre"] == "Escoba")
chk(esc["cuenta"] == "13452501" and esc["manual"] == "13452501", "ítem manual sigue en 13452501")
chk(docs["g1"]["cuenta"] == "14050502" and docs["g1"]["items"][0]["capa"] == "lexico", "papel viejo guarda ítems con capa")
chk(dia["debito"] == dia["credito"] and dia["filas"], f"día rehecho por construir y cuadra (D {dia['debito']} = C {dia['credito']})")
r = dia.get("reclasificaciones", [])
chk(len(r) == 1 and r[0]["version"] == VERSION and len(r[0]["cambios"]) == 2 and r[0]["fecha_hora"] == "2026-10-25T12:00:00", "rastro reclasificaciones[] en el día (S3)")
chk(nuevo["2026-08-31"] is LIB["2026-08-31"], "agosto no se toca")
p2 = plan(nuevo, "2026-09", m)
chk(p2["cambios"] == [], "ADR-021: reclasificar no es idempotente" if p2["cambios"] else "plan tras aplicar → 0 cambios (idempotente)")
chk(aplicar(nuevo, p2, m, cfg) == nuevo, "aplicar un plan vacío no cambia nada")

# guardar: una escritura, respaldo único
with tempfile.TemporaryDirectory() as t:
    ruta = Path(t) / "libro.json"; ruta.write_text(json.dumps(LIB), encoding="utf8")
    guardar(ruta, nuevo); resp = ruta.with_name(f"libro.antes-v{VERSION}.json")
    chk(resp.is_file() and json.loads(resp.read_text(encoding="utf8")) == LIB and json.loads(ruta.read_text(encoding="utf8")) == nuevo, "guardar: respaldo antes-v1.8.0 + libro nuevo")
    guardar(ruta, LIB)
    chk(json.loads(resp.read_text(encoding="utf8")) == LIB and not ruta.with_suffix(".tmp").exists(), "el respaldo no se pisa y no queda .tmp")

# sept. real (N3: < 30 s el mes)
real = Path("datos/libro.json")
if real.is_file():
    lib = json.loads(real.read_text(encoding="utf8")); mr = Motor.desde_archivos(str(Path("datos/clasificacion.json")))
    c = Path("datos/contable.json"); cfg_r = cfg | (json.loads(c.read_text(encoding="utf8")) if c.is_file() else {})
    t0 = time.perf_counter(); ps = plan(lib, "2026-09", mr); t1 = time.perf_counter(); ns = aplicar(lib, ps, mr, cfg_r); t2 = time.perf_counter()
    chk(t2 - t0 < 30, f"sept.: plan {t1 - t0:.2f} s + aplicar {t2 - t1:.2f} s < 30 s (N3); {len(ps['cambios'])} cambios en {len({x['fecha'] for x in ps['cambios']})} días")
    chk(all(ns[k]["diferencia"] == lib[k]["diferencia"] for k in ns if k.startswith("2026-09")), "sept.: ningún día pierde el cuadre (misma diferencia D − C)")
    chk(plan(ns, "2026-09", mr)["cambios"] == [], "sept.: segundo plan → 0 cambios")
    man = [(k, d["id"], d["cuenta"]) for k in lib for d in lib[k]["documentos"] if d.get("cuenta_manual")]
    chk(all(next(x for x in ns[k]["documentos"] if x["id"] == i)["cuenta"] == cu for k, i, cu in man), f"sept.: {len(man)} papel(es) con cuenta a mano intactos")
else: print("· sin datos/libro.json: se salta sept.")

print("TODO OK" if ok else "HAY FALLOS"); raise SystemExit(0 if ok else 1)
