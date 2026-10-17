"""Ingresos Diarios · Fotos de cierres de caja manuscritos → tabla → Excel.
Ejecuta:  python app.py   (abre http://127.0.0.1:5050)"""
from __future__ import annotations
import io, json, os, re, threading, webbrowser
from datetime import datetime
from pathlib import Path
import requests
from flask import Flask, jsonify, request, send_file, send_from_directory
try:
    from dotenv import load_dotenv; load_dotenv()
except ImportError:
    pass
from PIL import Image
from ocr_module import digitize, get_engine
from ocr_module import pdf as pdflib
from ocr_module import orientacion
from parser_module import Config, Esquema, parsear
from excel_export import construir_excel
from parser_module.contable.documentos import PARSERS, _base as _base_doc
from parser_module.contable import Clasificador, construir as construir_asientos, leer_texto, libro_a_excel, MARCA, completar_desde_cierre
from parser_module.contable.asientos import CATALOGO, CFG as CFG_ASIENTOS
from parser_module.contable import soporte, soporte_db, soporte_excel, proveedores as provs
from dataclasses import asdict
from datetime import date
from urllib.parse import urlsplit

BASE = Path(__file__).parent
DATOS = BASE / "datos"; DATOS.mkdir(exist_ok=True)
HIST = DATOS / "historial.json"
RUTA_ESQ, RUTA_ALIAS = DATOS / "esquema.json", DATOS / "alias_negocio.json"
ESQ = Esquema.cargar(RUTA_ESQ, Esquema.plantilla("restaurante_pyg"))   # primera vez: plantilla mínima de restaurante
CFG = Config.cargar(str(RUTA_ALIAS), ESQ)
LOCK = threading.Lock()
OLLAMA = os.getenv("LOCAL_VLM_URL", "http://localhost:11434/v1").rstrip("/")
app = Flask(__name__, static_folder="static", static_url_path="/static")
app.config["MAX_CONTENT_LENGTH"] = 40 * 1024 * 1024
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _leer_hist() -> dict:
    try: return json.loads(HIST.read_text(encoding="utf8"))
    except (FileNotFoundError, json.JSONDecodeError): return {}


def _guardar_hist(d: dict):
    tmp = HIST.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf8"); tmp.replace(HIST)


def _fila_limpia(f: dict) -> dict:
    v = f.get("valores") or {}
    ent = {c.clave: int(v.get(c.clave) or 0) for c in ESQ.entradas}
    todo = ESQ.evaluar(ent)                                   # las columnas calculadas las recalcula el servidor
    fact = []                                                 # cada factura (imagen) que compone el día, para poder auditarlo o reabrirlo
    for x in (f.get("facturas") or [])[:60]:
        xv = x.get("valores") or {}
        fact.append({"nombre": str(x.get("nombre", ""))[:120], "notas": str(x.get("notas", ""))[:300],
                     "valores": {c.clave: int(xv.get(c.clave) or 0) for c in ESQ.entradas}})
    return {"fecha": f.get("fecha", ""), "valores": {k: round(todo[k]) for k in ESQ.claves},
            "notas": str(f.get("notas", ""))[:500], "archivo": str(f.get("archivo", ""))[:200],
            "facturas": fact, "nfacturas": len(fact) or 1}


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "contable.html")


@app.get("/simple")
def index_simple():
    return send_from_directory(app.static_folder, "index.html")


def _esquema_json():
    from parser_module.plantillas import PLANTILLAS
    d = ESQ.to_dict(ui=True)
    d["plantillas"] = [{"id": k, "nombre": n, "esquema": Esquema.plantilla(k).to_dict(ui=True)} for k, (n, _) in PLANTILLAS.items()]
    return d


@app.get("/api/esquema")
def esquema_ver():
    return jsonify(_esquema_json())


@app.post("/api/esquema")
def esquema_guardar():
    """Define las columnas (nombre, tipo, sinónimos) antes o después de escanear. Las lecturas ya hechas se reinterpretan sin repetir el OCR."""
    global ESQ, CFG
    try: nuevo = Esquema.desde_dict(request.get_json(silent=True) or {})
    except ValueError as e: return jsonify(error=str(e)), 400
    with LOCK:
        nuevo.guardar(RUTA_ESQ); ESQ = nuevo
        CFG = Config.cargar(str(RUTA_ALIAS), ESQ)
    return jsonify(_esquema_json())


@app.get("/api/estado")
def estado():
    try:
        r = requests.get(OLLAMA.removesuffix("/v1") + "/api/tags", timeout=2)
        modelos = [m["name"] for m in r.json().get("models", [])]; ok = True
    except Exception:  # noqa: BLE001
        modelos, ok = [], False
    return jsonify(ollama=ok, modelos=modelos, modelo=os.getenv("LOCAL_VLM_MODEL", "qwen2.5vl:7b"))


@app.post("/api/escanear")
def escanear():
    f = request.files.get("foto")
    if not f: return jsonify(ok=False, error="No llegó ninguna foto."), 400
    motor, modelo = request.form.get("motor", "local"), request.form.get("modelo") or None
    try:
        eng = get_engine(motor, **({"model": modelo} if modelo and motor == "local" else {}))
    except Exception as e:  # noqa: BLE001
        return jsonify(ok=False, error=str(e))
    res = digitize(f.read(), eng)
    if not res.ok: return jsonify(ok=False, error=res.error)
    d = parsear(res.text, CFG, fuente=f.filename or "").to_dict(); d.pop("texto", None)
    return jsonify(ok=True, texto=res.text, segundos=res.seconds, modelo=res.model, cierre=d)


@app.post("/api/reparsear")
def reparsear():
    d = parsear((request.get_json(silent=True) or {}).get("texto", ""), CFG).to_dict(); d.pop("texto", None)
    return jsonify(cierre=d)


@app.post("/api/aprender")
def aprender():
    j = request.get_json(silent=True) or {}
    try: CFG.aprender(str(j.get("etiqueta", "")), str(j.get("campo", "")))
    except ValueError as e: return jsonify(error=str(e)), 400
    return jsonify(ok=True)


@app.get("/api/historial")
def hist_listar():
    return jsonify(filas=sorted(_leer_hist().values(), key=lambda f: f["fecha"], reverse=True))


@app.post("/api/historial")
def hist_guardar():
    j = request.get_json(silent=True) or {}
    filas = [_fila_limpia(f) for f in j.get("filas", [])]
    sin = [i + 1 for i, f in enumerate(filas) if not ISO.match(f["fecha"])]
    if sin: return jsonify(error="Faltan fechas válidas", filas=sin), 400
    rep = [f["fecha"] for f in filas]
    if len(set(rep)) != len(rep):
        return jsonify(error="Hay fechas repetidas en la tabla", duplicadas=sorted({x for x in rep if rep.count(x) > 1})), 400
    with LOCK:
        h = _leer_hist()
        choque = sorted(f["fecha"] for f in filas if f["fecha"] in h)
        if choque and not j.get("reemplazar"): return jsonify(conflicto=choque), 409
        for f in filas: h[f["fecha"]] = {**f, "guardado": datetime.now().isoformat(timespec="seconds")}
        _guardar_hist(h)
    return jsonify(ok=True, guardadas=len(filas), total=len(h))


@app.delete("/api/historial/<fecha>")
def hist_borrar(fecha):
    with LOCK:
        h = _leer_hist(); h.pop(fecha, None); _guardar_hist(h)
    return jsonify(ok=True)


def _enviar(filas, nombre):
    return send_file(io.BytesIO(construir_excel(filas, ESQ)), mimetype=XLSX, as_attachment=True, download_name=nombre)


@app.post("/api/excel")
def excel_tabla():
    filas = [_fila_limpia(f) for f in (request.get_json(silent=True) or {}).get("filas", [])]
    return _enviar(filas, f"ingresos_{datetime.now():%Y%m%d_%H%M}.xlsx")


@app.get("/api/excel/historial")
def excel_historial():
    d, h = request.args.get("desde", ""), request.args.get("hasta", "")
    filas = [f for f in _leer_hist().values() if (not d or f["fecha"] >= d) and (not h or f["fecha"] <= h)]
    return _enviar(filas, f"ingresos_historial_{datetime.now():%Y%m%d}.xlsx")


# ═════════════ LIBRO CONTABLE: papeles → documentos → asientos (débito/crédito) → tabla ═════════════
RUTA_LIBRO, RUTA_CONT = DATOS / "libro.json", DATOS / "contable.json"
CLASIF = Clasificador(str(DATOS / "clasificacion.json"))


def _cont_cfg() -> dict:
    try: c = json.loads(RUTA_CONT.read_text(encoding="utf8"))
    except (FileNotFoundError, json.JSONDecodeError): c = {}
    return {"puente_ingreso": CFG_ASIENTOS["puente_ingreso"], "puente_gasto": CFG_ASIENTOS["puente_gasto"], **c}


def _leer_libro() -> dict:
    try: return json.loads(RUTA_LIBRO.read_text(encoding="utf8"))
    except (FileNotFoundError, json.JSONDecodeError): return {}


def _guardar_libro(d: dict):
    tmp = RUTA_LIBRO.with_suffix(".tmp"); tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf8"); tmp.replace(RUTA_LIBRO)


def _clasificar(docs: list) -> list:
    completar_desde_cierre(docs)
    for d in docs:
        if d["tipo"] in ("gasto_caja", "factura", "caja_menor_manuscrito") and not d.get("cuenta"):
            r = CLASIF.clasificar(d["tercero"] if d["tipo"] == "factura" else "", d["detalle"], d["texto"])
            d["cuenta"], d["conf"], d["motivo"] = r["cuenta"], r["conf"], r["motivo"]
    return docs


@app.get("/api/contable/catalogo")
def cont_catalogo():
    return jsonify(cuentas=[{"codigo": c["codigo"], "nombre": c["nombre_diario"], "clase": c["clase"]} for c in CATALOGO.values()], config=_cont_cfg())


@app.post("/api/contable/pdf_info")
def cont_pdf_info():
    f = request.files.get("pdf")
    if not f: return jsonify(error="No llegó ningún PDF."), 400
    try: info = pdflib.info(f.read())
    except RuntimeError as e: return jsonify(error=str(e)), 400
    return jsonify(info)


CATEGORIAS = {"cierre": "cierre", "cierres": "cierre", "comanda": "comandas", "comandas": "comandas", "gasto": "gastos", "gastos": "gastos"}


def _categoria_por_nombre(ruta: str) -> str:
    """«15 SEPT/GASTOS/gastos_239.pdf» → gastos. Mira las carpetas y el prefijo del archivo."""
    partes = re.split(r"[\\/]", ruta or "")
    for p in reversed(partes):
        base = re.sub(r"\.[a-z0-9]+$", "", p.lower())
        for k, v in CATEGORIAS.items():
            if base == k or re.match(rf"{k}(?![a-z])", base): return v
    return ""


@app.get("/api/contable/capacidades")
def cont_capacidades():
    return jsonify(giro_automatico=orientacion.tesseract_disponible(), pdf=bool(_pdf_ok()))


def _pdf_ok() -> bool:
    try: pdflib._pm(); return True
    except RuntimeError: return False


def _leer_hoja(img_bytes: bytes, eng, giro="auto") -> tuple:
    """Una hoja (foto o página escaneada) → (texto con varios papeles separados por MARCA, segundos, grados girados)."""
    png, grados = orientacion.preparar_pagina(img_bytes, giro)
    trozos = orientacion.separar(Image.open(io.BytesIO(png)).convert("RGB"))
    textos, seg = [], 0.0
    for t in trozos:
        b = io.BytesIO(); t.save(b, "PNG")
        res = digitize(b.getvalue(), eng)
        if not res.ok: raise RuntimeError(res.error)
        textos.append(res.text); seg += res.seconds
    return f"\n{MARCA}\n".join(textos), round(seg, 2), grados


@app.post("/api/contable/escanear")
def cont_escanear():
    """Una foto, o UNA página de un PDF (texto digital si lo tiene; si no, se lee como imagen con el OCR).
    La categoría (cierre/comandas/gastos) viene del formulario o de la carpeta/nombre del archivo."""
    f = request.files.get("foto")
    if not f: return jsonify(ok=False, error="No llegó ningún archivo."), 400
    motor, modelo = request.form.get("motor", "local"), request.form.get("modelo") or None
    nombre = request.form.get("ruta") or f.filename or ""
    categoria = request.form.get("categoria", "") or _categoria_por_nombre(nombre)
    giro = request.form.get("giro", "auto"); giro = giro if giro == "auto" else int(giro)
    data = f.read(); fuente, segundos, grados = "ocr", 0, 0
    try:
        if (f.filename or "").lower().endswith(".pdf") or data[:4] == b"%PDF":
            texto, img = pdflib.pagina(data, int(request.form.get("pagina") or 1), como_imagen=request.form.get("como_imagen") == "1")
            if texto is not None: fuente = "texto"
        else: texto, img = None, data
        if texto is None:
            eng = get_engine(motor, **({"model": modelo} if modelo and motor == "local" else {}))
            texto, segundos, grados = _leer_hoja(img, eng, giro)
    except Exception as e:  # noqa: BLE001
        return jsonify(ok=False, error=str(e))
    docs = _clasificar(leer_texto(texto, categoria))
    for d in docs: d["origen"] = nombre
    return jsonify(ok=True, texto=texto, segundos=segundos, fuente=fuente, grados=grados, categoria=categoria, documentos=docs)


@app.post("/api/contable/releer")
def cont_releer():
    """Cambiaste el tipo de un papel (p. ej. de factura a comanda): se vuelve a leer su texto con el tipo correcto."""
    j = request.get_json(silent=True) or {}; tipo = j.get("tipo", "")
    if tipo != "otro" and tipo not in PARSERS: return jsonify(error="Tipo desconocido"), 400
    if tipo == "otro":
        d = _base_doc("otro", j.get("texto", "")); d["contar"] = False
    else: d = PARSERS[tipo](j.get("texto", ""))
    return jsonify(documento=_clasificar([d])[0])


@app.post("/api/contable/asientos")
def cont_asientos():
    j = request.get_json(silent=True) or {}
    r = construir_asientos(j.get("fecha", ""), _clasificar(j.get("documentos", [])), j.get("banco", {}), _cont_cfg(), j.get("cierre"))
    return jsonify(r)


@app.post("/api/contable/aprender")
def cont_aprender():
    j = request.get_json(silent=True) or {}
    if str(j.get("cuenta", "")) not in CATALOGO: return jsonify(error="Cuenta desconocida"), 400
    CLASIF.aprender(str(j["cuenta"]), str(j.get("tercero", "")), str(j.get("detalle", "")))
    return jsonify(ok=True)


@app.get("/api/contable/libro")
def cont_libro():
    return jsonify(dias=sorted(_leer_libro().values(), key=lambda d: d["fecha"], reverse=True))


@app.post("/api/contable/libro")
def cont_confirmar():
    j = request.get_json(silent=True) or {}; fecha = str(j.get("fecha", ""))
    if not ISO.match(fecha): return jsonify(error="Falta la fecha del día"), 400
    r = construir_asientos(fecha, j.get("documentos", []), j.get("banco", {}), _cont_cfg(), j.get("cierre"))
    if not r["filas"] and not r["pendientes"]: return jsonify(error="El día no tiene asientos"), 400   # R10: los pendientes también se guardan
    with LOCK:
        lib = _leer_libro()
        if fecha in lib and not j.get("reemplazar"): return jsonify(conflicto=[fecha]), 409
        lib[fecha] = dict(fecha=fecha, documentos=r["documentos"], banco=j.get("banco", {}), cierre=j.get("cierre") or {}, cruces=r["cruces"], filas=r["filas"], pendientes=r["pendientes"], debito=r["debito"], credito=r["credito"],
                          diferencia=r["diferencia"], guardado=datetime.now().isoformat(timespec="seconds"))
        _guardar_libro(lib)
    return jsonify(ok=True, dias=len(lib), diferencia=r["diferencia"])


@app.delete("/api/contable/libro/<fecha>")
def cont_borrar(fecha):
    with LOCK:
        lib = _leer_libro(); lib.pop(fecha, None); _guardar_libro(lib)
    return jsonify(ok=True)


@app.get("/api/contable/excel")
def cont_excel():
    d, h = request.args.get("desde", ""), request.args.get("hasta", "")
    lib = {k: v for k, v in _leer_libro().items() if (not d or k >= d) and (not h or k <= h)}
    c = _cont_cfg()
    rs = {k: construir_asientos(k, v.get("documentos", []), v.get("banco", {}), c, v.get("cierre")) for k, v in lib.items()}   # R9/ADR-002: filas y DATOS OCR del mismo cálculo
    dias, datos = {k: r["filas"] for k, r in rs.items()}, {k: r["datos"] for k, r in rs.items()}
    cambios = [f"{k}: cambió desde que se confirmó ({lib[k].get('guardado', 's/f')}): guardado débito {lib[k].get('debito', 0):,} · crédito {lib[k].get('credito', 0):,}; "
               f"hoy débito {r['debito']:,} · crédito {r['credito']:,}. Revisa el día o vuelve a confirmarlo".replace(",", ".")
               for k, r in sorted(rs.items()) if (lib[k].get("debito"), lib[k].get("credito")) != (r["debito"], r["credito"])]   # FIX-6: se recalcula con la config de hoy
    return send_file(io.BytesIO(libro_a_excel(dias, c.get("negocio", ""), c.get("nit", ""), datos, cambios)), mimetype=XLSX, as_attachment=True,
                     download_name=f"reporte_contable_{datetime.now():%Y%m%d}.xlsx")


# ═════════════ DOCUMENTO SOPORTE (Res. DIAN 167/2021): compras → semanas por proveedor → documentos numerados ═════════════
RUTA_SOPORTE = DATOS / "soporte.db"


@app.before_request
def _revisar_origen():
    """T1 de 03: otra página web no puede hacer POST/DELETE a localhost (CSRF) ni por DNS rebinding. Host y Origin deben ser locales."""
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        permitidos = {"127.0.0.1", "localhost"}
        if (request.host.rsplit(":", 1)[0] if not request.host.startswith("[") else request.host) not in permitidos:
            return jsonify(error="Host no permitido"), 403
        o = request.headers.get("Origin")
        if o is not None and (urlsplit(o).netloc != request.host or urlsplit(o).scheme not in ("http", "https")):
            return jsonify(error="Origen no permitido"), 403


def _sop_con():
    return soporte_db.abrir(RUTA_SOPORTE)


def _sop_cfg() -> dict:
    c = _cont_cfg()
    return {k: c[k] for k in soporte.DEFECTO if k in c}


def _doc_json(d) -> dict:
    return dict(id=d.id, numero=f"{d.prefijo}-{d.numero}", proveedor=d.proveedor.nombre, semana=d.semana, fecha_generacion=d.fecha_generacion,
                total=d.total, estado=d.estado, lineas=[asdict(l) for l in d.lineas])


def _grupo_json(g) -> dict:
    return dict(proveedor_id=g.proveedor.id if g.proveedor else None, tercero=g.tercero, semana=g.semana, lunes=g.lunes, domingo=g.domingo,
                total=g.total, fecha_limite=g.fecha_limite, estado=g.estado, dias_restantes=g.dias_restantes, registrado=g.proveedor is not None,
                compras=[asdict(c) for c in g.compras])


def _documentos(con, ids: list[int] | None = None) -> list:
    """Lee documentos de la base; `fecha_limite` no se guarda, se recalcula con la config de hoy."""
    c = soporte.config(_sop_cfg())
    docs = []
    for r in con.execute("SELECT * FROM documento WHERE clase = 'DS' ORDER BY id"):
        if ids is not None and r["id"] not in ids: continue
        p = provs.obtener(con, r["proveedor_id"])
        ls = [soporte.Linea(l["fecha_compra"], l["origen_fecha"], l["origen_doc_id"], l["descripcion"], l["valor"])
              for l in con.execute("SELECT * FROM linea WHERE documento_id = ? ORDER BY fecha_compra, origen_doc_id", (r["id"],))]
        y, w = r["semana_iso"].split("-W")
        lim = soporte.fecha_limite(date.fromisocalendar(int(y), int(w), 1), c["regla_plazo"], c["festivos"]).isoformat()
        docs.append(soporte.Documento(r["id"], r["prefijo"], r["numero"], p, r["semana_iso"], r["fecha_generacion"], r["total"], ls, lim, r["estado"], r["iva"]))
    return docs


@app.get("/api/soporte/semanas")
def sop_semanas():
    desde, hasta = request.args.get("desde", ""), request.args.get("hasta", "")
    if any(x and not ISO.match(x) for x in (desde, hasta)): return jsonify(error="Fecha inválida"), 400
    con = _sop_con()
    try:
        try: gs = soporte.semanas(_leer_libro(), con, _sop_cfg(), desde=desde, hasta=hasta)
        except ValueError as e: return jsonify(error=f"contable.json: {e}"), 400
        return jsonify(semanas=[_grupo_json(g) for g in gs])
    finally: con.close()


@app.post("/api/soporte/generar")
def sop_generar():
    j = request.get_json(silent=True) or {}
    sel = j.get("semanas")
    if not isinstance(sel, list) or not sel or len(sel) > 200 or not all(isinstance(x, dict) for x in sel): return jsonify(error="Elija al menos una semana"), 400
    with LOCK:
        con = _sop_con()
        try:
            try: gs = soporte.semanas(_leer_libro(), con, _sop_cfg())   # los grupos se recalculan en el servidor: el cliente solo elige
            except ValueError as e: return jsonify(error=f"contable.json: {e}"), 400
            elegidos = []
            for x in sel:
                g = next((g for g in gs if g.semana == x.get("semana") and ((g.proveedor and g.proveedor.id == x.get("proveedor_id"))
                                                                           or (not g.proveedor and x.get("proveedor_id") is None and g.tercero == x.get("tercero")))), None)
                if g is None: return jsonify(error=f"No existe la semana {x.get('semana')!s:.20} de ese proveedor"), 400
                elegidos.append(g)
            try: docs = soporte.generar(con, elegidos, bool(j.get("confirmar_vencidos")))
            except soporte.NoSeGenera as e: return jsonify(error=str(e)), 409
            except soporte_db.RangoAgotado as e: return jsonify(error=str(e)), 409
            return jsonify(documentos=[_doc_json(d) for d in docs])
        finally: con.close()


@app.get("/api/soporte/excel")
def sop_excel():
    try: ids = [int(x) for x in request.args["ids"].split(",") if x] if request.args.get("ids") else None
    except ValueError: return jsonify(error="ids inválidos"), 400
    con = _sop_con()
    try:
        try: docs = _documentos(con, ids)
        except ValueError as e: return jsonify(error=f"contable.json: {e}"), 400
    finally: con.close()
    if not docs: return jsonify(error="No hay documentos para exportar"), 404
    return send_file(io.BytesIO(soporte_excel.libro(docs)), mimetype=XLSX, as_attachment=True, download_name=f"documento_soporte_{datetime.now():%Y%m%d}.xlsx")


@app.get("/api/proveedores")
def prov_listar():
    con = _sop_con()
    try: return jsonify(proveedores=[asdict(provs.obtener(con, r[0])) for r in con.execute("SELECT id FROM proveedor ORDER BY nombre")])
    finally: con.close()


@app.post("/api/proveedores")
def prov_guardar():
    j = request.get_json(silent=True)
    if not isinstance(j, dict): return jsonify(error="Falta el proveedor"), 400
    with LOCK:
        con = _sop_con()
        try:
            p = provs.guardar(con, j)
            if j.get("alias_ocr"): provs.asociar(con, str(j["alias_ocr"]), p.id, bool(j.get("reasignar")))
            return jsonify(proveedor=asdict(p))
        except provs.DatosIncompletos as e: return jsonify(error=str(e)), 400
        finally: con.close()


if __name__ == "__main__":
    puerto = int(os.getenv("PORT", "5050"))
    if os.getenv("NO_BROWSER") != "1":
        threading.Timer(1.2, lambda: webbrowser.open(f"http://127.0.0.1:{puerto}")).start()
    app.run(host="127.0.0.1", port=puerto, threaded=True)
