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
r = cl.post(URL + "aaaa0001", json={"cambios": {"fecha": "2026-09-15"}})
chk(r.status_code == 400 and "fecha" in r.get_json()["error"], "editar: fecha válida tampoco es editable (FIX-6) → 400")
chk(json.loads(web.RUTA_LIBRO.read_text(encoding="utf-8"))[FECHA]["documentos"][0].get("fecha") == "2026-09-14", "editar fecha: el recibo no cambia")
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

# FIX-1: relectura sin ese número → el revisado se conserva; dos nuevos con la misma clave → el previo se usa una sola vez
r = cl.post("/api/contable/libro", json={"fecha": FECHA, "documentos": [venta("nnnn0004", "101", 20000, "validado")], "reemplazar": True})
chk(r.status_code == 200 and doc("aaaa0001")["consumo"] == 10000 and doc("aaaa0003")["consumo"] == 36000, "releer sin ese número: los revisados 100 y 102 se conservan")
chk(len([d for d in dia()["documentos"] if d["tipo"] == "venta"]) == 3, "releer sin ese número: no sobran ni faltan recibos")
r = cl.post("/api/contable/libro", json={"fecha": FECHA, "documentos": [venta("nnnn0005", "100", 1, "dudoso"), venta("nnnn0006", "100", 2, "dudoso")], "reemplazar": True})
c100 = [d for d in dia()["documentos"] if d["tipo"] == "venta" and d["numero"] == "100"]
chk(r.status_code == 200 and sum(d["id"] == "aaaa0001" for d in c100) == 1, "dos nuevos con la misma clave: el revisado entra una sola vez")
chk(sorted(d["id"] for d in c100) == ["aaaa0001", "nnnn0006"], "dos nuevos con la misma clave: el segundo queda como lectura nueva")

# M-13 T3: marcadores de foto y releer una foto ya resuelta
from PIL import Image
import io
from parser_module.contable import faltantes, recortes
web.RUTA_RECORTES = T / "recortes"
buf = io.BytesIO(); Image.new("RGB", (3000, 2000), "white").save(buf, "PNG")
ms = web._marcadores_de_foto(buf.getvalue(), [85628, 85630], "sep/85627 al 630.jpg", [venta("v1", "85627", 1000, "validado")])
chk([m["numero"] for m in ms] == ["85628", "85630"] and all(m["tipo"] == "faltante" and m["fecha"] == FECHA for m in ms), "marcadores: uno por número, con la fecha de la foto")
foto = recortes.abrir(ms[0]["recorte"], web.RUTA_RECORTES)
chk(ms[0]["recorte"] == ms[1]["recorte"] and max(Image.open(io.BytesIO(foto)).size) <= 1600, "marcadores: foto entera guardada ≤ 1600 px, una sola")
chk(web._marcadores_de_foto(b"no es imagen", [1], "x.jpg", [])[0]["recorte"] is None, "foto que no se puede guardar → recorte null")
orig = "sep/85627 al 630.jpg"
hecho = faltantes.anotar(faltantes.crear([85628], orig, FECHA, None)[0], {k: v for k, v in _base("venta", "").items() if k not in ("id", "tipo", "avisos")} | {"consumo": 5000, "efectivo": 5000, "medio": "Efectivo"})
cerrado = faltantes.cerrar(faltantes.crear([85630], orig, FECHA, None)[0], "no existe")
nuevo = faltantes.crear([85628, 85630, 85631], orig, FECHA, None)
res = web._conservar_revisados([hecho, cerrado], nuevo)
chk([d["numero"] for d in res if d["tipo"] == "faltante" and d["estado"] == "falta"] == ["85631"], "releer foto resuelta: solo vuelve el faltante aún abierto")
chk(sum(d["numero"] == "85628" for d in res) == 1 and any(d["estado"] == "no_existe" for d in res), "releer foto resuelta: sin duplicar el anotado, el «no existe» se conserva")
lib = json.loads(web.RUTA_LIBRO.read_text(encoding="utf8")); lib[FECHA]["documentos"] += [hecho, cerrado]; web.RUTA_LIBRO.write_text(json.dumps(lib), encoding="utf8")
r = cl.post("/api/contable/libro", json={"fecha": FECHA, "documentos": [venta("zzzz0001", "101", 20000, "validado")] + nuevo, "reemplazar": True})
chk(r.status_code == 200 and [d["numero"] for d in dia()["documentos"] if d["tipo"] == "faltante" and d["estado"] == "falta"] == ["85631"], "POST /libro: releer foto resuelta no duplica marcadores")

# FIX-9: el catálogo se arma una vez por arranque (no se reescribe en cada escaneo); confirmar lo invalida
from parser_module.contable import catalogo as cat
llamadas = []
cat.cargar, cat.desde_libro = (lambda *a, **k: llamadas.append("cargar") or {}), (lambda *a, **k: llamadas.append("desde_libro") or {"cafe": 3000})
web._PRECIOS = None
chk(web._catalogo() == {"cafe": 3000} and web._catalogo() == {"cafe": 3000} and llamadas == ["desde_libro"], "catálogo: dos escaneos → se arma y escribe una sola vez")
r = cl.post(URL + "aaaa0001", json={})
chk(r.status_code == 200 and web._PRECIOS is None and web._catalogo() == {"cafe": 3000} and llamadas.count("desde_libro") == 2, "catálogo: confirmar en Revisión lo vuelve a armar")

# FIX-14: catalogo.json ya con precios + confirmar un precio nuevo → aparece en _catalogo()
cat.cargar = lambda *a, **k: {"cafe": 3000}
cat.desde_libro = lambda *a, **k: {"cafe": 3000, "te": 2000}
web._PRECIOS = None
chk(web._catalogo() == {"cafe": 3000, "te": 2000}, "catálogo con precios en archivo: el primer _catalogo() rehace desde el libro")
cat.desde_libro = lambda *a, **k: {"cafe": 3000, "te": 2000, "pan": 1500}
r = cl.post(URL + "aaaa0001", json={})
chk(r.status_code == 200 and web._catalogo().get("pan") == 1500, "catálogo con precios + confirmar un precio nuevo → aparece en _catalogo()")

# FIX-10: un recibo sin número se reemplaza por id (antes cada edición lo volvía a sumar)
dsn = T / "ref_sin_numero.json"
for v in (1000, 2000): referencia.agregar(dsn, "2026-09", venta("ssss0001", "", v, "revisado"))
referencia.agregar(dsn, "2026-09", venta("ssss0002", "", 3000, "revisado"))
sn = json.loads(dsn.read_text(encoding="utf8"))["documentos"]
chk(sorted((r["documento"]["id"], r["documento"]["consumo"]) for r in sn) == [("ssss0001", 2000), ("ssss0002", 3000)], "referencia.agregar: sin número se reemplaza por id")

print("\nTODO BIEN" if not fallos else f"\n{len(fallos)} FALLO(S)")
raise SystemExit(1 if fallos else 0)
