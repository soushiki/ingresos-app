"""T10 · revisión de recibos dudosos (R8): listar, confirmar, editar y releer-sin-pisar. Valida entradas (400/404).
    python probar_revision.py"""
import json, tempfile
from pathlib import Path
import app as web
from parser_module.contable.documentos import _base
from parser_module.contable.asientos import estado_de
from parser_module.contable import referencia

fallos = []
def chk(cond, msg):
    print(("✓ " if cond else "✗ ") + msg)
    if not cond: fallos.append(msg)

T = Path(tempfile.mkdtemp())
web.RUTA_LIBRO, web.RUTA_CONT, web.RUTA_REF = T / "libro.json", T / "contable.json", T / "referencia"
web.RUTA_SOPORTE = T / "soporte.db"

def venta(id, numero, consumo, estado, **kw):
    d = _base("venta", f"COMANDA {numero}"); d.update(id=id, numero=numero, fecha="2026-09-14", consumo=consumo, efectivo=consumo, medio="Efectivo",
                                                        origen="sep/foto1.jpg#1", estado=estado, motivos=["x no cuadra"] if estado == "dudoso" else [], **kw)
    return d

FECHA = "2026-09-14"
docs = [venta("aaaa0001", "100", 10000, "dudoso", avisos=["Los pagos (75.000) no suman consumo"]), venta("aaaa0002", "101", 20000, "validado"), venta("aaaa0003", "102", 30000, "dudoso")]
lib = {FECHA: web.construir_asientos(FECHA, docs, {}, web._cont_cfg(), None)}
lib[FECHA].update(fecha=FECHA, banco={}, cierre={})
web.RUTA_LIBRO.write_text(json.dumps(lib), encoding="utf8")
cl = web.app.test_client()
URL = f"/api/contable/revision/{FECHA}/"
def dia(): return json.loads(web.RUTA_LIBRO.read_text(encoding="utf8"))[FECHA]
def doc(i): return next(d for d in dia()["documentos"] if d["id"] == i)

# listar
r = cl.get("/api/contable/revision?desde=2026-09-01&hasta=2026-09-30"); j = r.get_json()
chk(r.status_code == 200 and sorted(x["id"] for x in j["recibos"]) == ["aaaa0001", "aaaa0003"] and j["total"] == 2, "listar: solo los dudosos del rango")
chk(j["recibos"][0]["motivos"] == ["x no cuadra"] and j["recibos"][0]["fecha"] == FECHA, "listar: trae motivos y fecha")
chk(cl.get("/api/contable/revision?desde=2026-10-01&hasta=2026-10-30").get_json()["recibos"] == [], "listar: fuera del rango no sale nada")
chk(cl.get("/api/contable/revision?desde=2026-09-01&hasta=2026-09-30&estado=validado").get_json()["total"] == 1, "listar: filtra por estado")
chk(cl.get("/api/contable/revision?desde=hoy").status_code == 400, "listar: fecha mala → 400")
chk(cl.get("/api/contable/revision").status_code == 400, "listar: sin desde → 400")
chk(cl.get("/api/contable/revision?desde=2026-09-01&estado=otro").status_code == 400, "listar: estado desconocido → 400")

# validación de entradas
chk(cl.post(f"/api/contable/revision/hoy/aaaa0001").status_code == 400, "confirmar: fecha mala → 400")
chk(cl.post(URL + "../x").status_code in (400, 404), "confirmar: id con ruta → rechazado")
chk(cl.post(URL + "ZZ'; drop").status_code in (400, 404), "confirmar: id con basura → rechazado")
chk(cl.post(URL + "bbbb9999").status_code == 404, "confirmar: id inexistente → 404")
chk(cl.post("/api/contable/revision/2026-01-01/aaaa0001").status_code == 404, "confirmar: día inexistente → 404")
chk(cl.post(URL + "aaaa0001", json={"cambios": {"consumo": "12"}}).status_code == 400, "editar: número como texto → 400")
chk(cl.post(URL + "aaaa0001", json={"cambios": {"consumo": -5}}).status_code == 400, "editar: negativo → 400")
chk(cl.post(URL + "aaaa0001", json={"cambios": {"consumo": True}}).status_code == 400, "editar: booleano → 400")
chk(cl.post(URL + "aaaa0001", json={"cambios": {"estado": "validado"}}).status_code == 400, "editar: campo no permitido → 400")
chk(cl.post(URL + "aaaa0001", json={"cambios": {"fecha": "ayer"}}).status_code == 400, "editar: fecha mala → 400")
chk(cl.post(URL + "aaaa0001", json={"cambios": [1]}).status_code == 400, "editar: cambios no objeto → 400")
chk(cl.post(URL + "aaaa0001", data=b"x" * 70000, content_type="application/json").status_code == 413, "cuerpo enorme → 413")
chk(cl.post(URL + "aaaa0001", json={}, headers={"Origin": "http://evil.example.com"}).status_code == 403, "Origen ajeno → 403")
chk(estado_de(doc("aaaa0001")) == "dudoso", "las entradas malas no cambiaron nada")

# confirmar: queda revisado, el día se recalcula, entra a la referencia
antes = dia()["debito"]
r = cl.post(URL + "aaaa0001")
chk(r.status_code == 200 and r.get_json()["estado"] == "revisado" and estado_de(doc("aaaa0001")) == "revisado", "confirmar: queda «revisado»")
chk(dia()["debito"] == antes and doc("aaaa0001")["motivos"] == [], "confirmar sin cambios: mismo total, sin motivos")
chk(doc("aaaa0001")["avisos"] == [] and doc("aaaa0001")["avisos_resueltos"] == ["Los pagos (75.000) no suman consumo"],
    "revisado (FIX-13 del ciclo OCR): confirmar pasa el aviso viejo del OCR a avisos_resueltos")
chk(not any(x["id"] == "aaaa0001" and x["motivo"] for x in web.construir_asientos(FECHA, dia()["documentos"], {}, web._cont_cfg(), None)["datos"]),
    "revisado (FIX-13 del ciclo OCR): sin Motivo en DATOS OCR")
ref = json.loads((web.RUTA_REF / "referencia_2026-09.json").read_text(encoding="utf8"))
chk([r["numero"] for r in ref["documentos"]] == ["100"] and ref["documentos"][0]["foto"] == "sep/foto1.jpg", "confirmar: entra a la referencia del mes")

# editar: cambia el valor, recalcula el día y actualiza la referencia
r = cl.post(URL + "aaaa0003", json={"cambios": {"consumo": 35000, "efectivo": 35000, "medio": "Efectivo"}})
chk(r.status_code == 200 and doc("aaaa0003")["consumo"] == 35000 and estado_de(doc("aaaa0003")) == "revisado", "editar: valor nuevo y «revisado»")
chk(dia()["debito"] == antes + 5000, f"editar: el día se recalcula (+5000): {dia()['debito']} vs {antes}")
ref = json.loads((web.RUTA_REF / "referencia_2026-09.json").read_text(encoding="utf8"))
chk(sorted(r["numero"] for r in ref["documentos"]) == ["100", "102"] and ref["documentos"][1]["documento"]["consumo"] == 35000, "editar: la referencia tiene el valor corregido")
cl.post(URL + "aaaa0003", json={"cambios": {"consumo": 36000}})
ref = json.loads((web.RUTA_REF / "referencia_2026-09.json").read_text(encoding="utf8"))
chk(len(ref["documentos"]) == 2, "editar dos veces no duplica en la referencia")
chk(cl.get("/api/contable/revision?desde=2026-09-01&estado=revisado").get_json()["total"] == 2, "listar: los revisados salen con estado=revisado y ya no como dudosos")
chk(cl.get("/api/contable/revision?desde=2026-09-01").get_json()["total"] == 0, "listar: ya no quedan dudosos")

# congelar reconoce el estado nuevo (T4: estado_de, no solo la bandera vieja)
dest = T / "ref_congelada.json"
nuevo = json.loads(web.RUTA_LIBRO.read_text(encoding="utf8")); nuevo[FECHA]["documentos"][1].pop("revisado", None)
nuevo[FECHA]["documentos"][0].pop("revisado", None)
(T / "l2.json").write_text(json.dumps(nuevo), encoding="utf8")
c = referencia.congelar(T / "l2.json", "2026-09", dest)
chk(len(c["documentos"]) >= 1 and all(r["documento"]["estado"] == "revisado" for r in c["documentos"]), "congelar usa estado == «revisado»")

# releer NO pisa un «revisado»: el mismo día vuelto a guardar con lecturas nuevas (otros ids) conserva lo revisado
rel = [venta("nnnn0001", "100", 99999, "dudoso"), venta("nnnn0002", "101", 20000, "validado"), venta("nnnn0003", "102", 88888, "dudoso")]
r = cl.post("/api/contable/libro", json={"fecha": FECHA, "documentos": rel, "reemplazar": True})
chk(r.status_code == 200, f"releer: el día se vuelve a guardar ({r.status_code})")
chk(doc("aaaa0001")["consumo"] == 10000 and estado_de(doc("aaaa0001")) == "revisado", "releer: el 100 revisado sigue igual")
chk(doc("aaaa0003")["consumo"] == 36000 and estado_de(doc("aaaa0003")) == "revisado", "releer: el 102 editado conserva la corrección")
chk(not any(d["id"] in ("nnnn0001", "nnnn0003") for d in dia()["documentos"]), "releer: las lecturas nuevas de los revisados no entran")
chk(any(d["id"] == "nnnn0002" for d in dia()["documentos"]), "releer: el no revisado sí se actualiza")
chk(len([d for d in dia()["documentos"] if d["tipo"] == "venta"]) == 3, "releer: no se duplican recibos")

print("\nTODO BIEN" if not fallos else f"\n{len(fallos)} FALLO(S)")
raise SystemExit(1 if fallos else 0)
