"""Ingresos Diarios · Fotos de cierres de caja manuscritos → tabla → Excel.
Ejecuta:  python app.py   (abre http://127.0.0.1:5050)"""
from __future__ import annotations
import copy, io, json, os, re, threading, webbrowser
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
from ocr_module.digitos import numeros_tesseract
from parser_module import Config, Esquema, parsear
from excel_export import construir_excel
from parser_module.contable.documentos import PARSERS, _base as _base_doc
from parser_module.contable import Clasificador, construir as construir_asientos, leer_texto, libro_a_excel, MARCA, completar_desde_cierre
from parser_module.contable.asientos import CATALOGO, CFG as CFG_ASIENTOS, estado_de
from parser_module.contable import referencia
from parser_module.contable import soporte, soporte_db, soporte_excel, proveedores as provs, recortes, relectura
from parser_module.contable.exportar import crudo as crudo_json, leer_crudo, CrudoInvalido
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
SIN_OCR = os.getenv("SIN_OCR") == "1"   # T20/ADR-004: PC del contador, no lee fotos (no busca a Ollama); importa los datos crudos
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
    """T20: sin_ocr = este PC no puede leer fotos con la IA local (SIN_OCR=1 u Ollama apagado); la pestaña ① ofrece importar."""
    if SIN_OCR: return jsonify(ollama=False, sin_ocr=True, forzado=True, modelos=[], modelo="")
    try:
        r = requests.get(OLLAMA.removesuffix("/v1") + "/api/tags", timeout=2)
        modelos = [m["name"] for m in r.json().get("models", [])]; ok = True
    except Exception:  # noqa: BLE001
        modelos, ok = [], False
    return jsonify(ollama=ok, sin_ocr=not ok, forzado=False, modelos=modelos, modelo=os.getenv("LOCAL_VLM_MODEL", "qwen2.5vl:7b"))


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


def _motor(eng):
    """El motor de C5: un recorte (PIL) → texto, con el mismo OCR de siempre (digitize). Un error sube."""
    def leer(img):
        b = io.BytesIO(); img.save(b, "PNG"); res = digitize(b.getvalue(), eng)
        if not res.ok: raise RuntimeError(res.error)
        return res.text
    leer.nombre = getattr(eng, "model", None) or getattr(eng, "name", "local"); return leer


def _catalogo() -> dict:
    """R6: precios de la carta (datos/catalogo.json); si está vacío se arma del libro. Sin libro → {} (R6 no hace nada)."""
    from parser_module.contable import catalogo
    precios = catalogo.cargar()
    if precios: return precios
    try: return catalogo.desde_libro(_leer_libro())
    except Exception: return {}   # noqa: BLE001


def _leer_hoja(img_bytes: bytes, eng, giro="auto", categoria="", nombre="", completa=True) -> dict:
    """Una hoja (foto o página escaneada) → documentos (T8: cada venta por C5 leer_recibo, R5 con el nombre de la foto),
    texto con los papeles separados por MARCA, segundos, grados girados y avisos de la hoja («Falta el recibo …»)."""
    png, grados = orientacion.preparar_pagina(img_bytes, giro)
    esperados = relectura.numeros_de_nombre(nombre) if categoria in ("", "comandas") else None   # T8b: cuántos papeles trae la foto
    trozos = orientacion.separar(Image.open(io.BytesIO(png)).convert("RGB"), esperados=len(esperados) if esperados else None)
    h = relectura.leer_hoja(trozos, _motor(eng), categoria, nombre, completa=completa, carpeta=RUTA_RECORTES, separar=orientacion.separar,
                         catalogo=_catalogo(), leer_digitos=numeros_tesseract)
    return {**h, "grados": grados}


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
    data = f.read(); fuente, segundos, grados, docs, avisos = "ocr", 0, 0, None, []
    try:
        es_pdf = (f.filename or "").lower().endswith(".pdf") or data[:4] == b"%PDF"
        if es_pdf:
            texto, img = pdflib.pagina(data, int(request.form.get("pagina") or 1), como_imagen=request.form.get("como_imagen") == "1")
            if texto is not None: fuente = "texto"
        else: texto, img = None, data
        if texto is None:
            if SIN_OCR: raise RuntimeError("Este PC está en modo sin OCR: lee las fotos en el PC de lectura e importa aquí sus datos crudos (.json).")
            eng = get_engine(motor, **({"model": modelo} if modelo and motor == "local" else {}))
            completa = not es_pdf or pdflib.info(data)["paginas"] == 1     # R5: una página de un PDF largo no trae todo el lote del nombre
            h = _leer_hoja(img, eng, giro, categoria, nombre, completa)
            texto, segundos, grados, docs, avisos = h["texto"], h["segundos"], h["grados"], h["documentos"], h["avisos"]
    except Exception as e:  # noqa: BLE001
        return jsonify(ok=False, error=str(e))
    docs = _clasificar(leer_texto(texto, categoria) if docs is None else docs)
    for d in docs: d["origen"] = nombre
    return jsonify(ok=True, texto=texto, segundos=segundos, fuente=fuente, grados=grados, categoria=categoria, documentos=docs, avisos=avisos)


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


RUTA_RECORTES = DATOS / "recortes"


@app.get("/api/contable/recorte/<nombre>")
def cont_recorte(nombre):
    """ADR-006: sirve solo nombres <16 hex>.jpg de datos/recortes."""
    b = recortes.abrir(nombre, RUTA_RECORTES)
    if b is None: return jsonify(error="sin recorte"), 404
    return send_file(io.BytesIO(b), mimetype="image/jpeg")


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
        b = _bloqueos(fecha, r["documentos"])
        if b: return jsonify(error="R7: el día tiene compras de un documento soporte transmitido", bloqueos=b), 409
        previos = [d for d in lib.get(fecha, {}).get("documentos", []) if estado_de(d) == "revisado"]
        if previos:   # T10/R8: volver a leer un día nunca pisa un recibo «revisado»
            r = construir_asientos(fecha, _conservar_revisados(previos, j.get("documentos", [])), j.get("banco", {}), _cont_cfg(), j.get("cierre"))
        lib[fecha] = _dia(fecha, r, j.get("banco", {}), j.get("cierre"))
        _guardar_libro(lib)
    return jsonify(ok=True, dias=len(lib), diferencia=r["diferencia"])


def _dia(fecha: str, r: dict, banco: dict, cierre) -> dict:
    return dict(fecha=fecha, documentos=r["documentos"], banco=banco, cierre=cierre or {}, cruces=r["cruces"], filas=r["filas"], pendientes=r["pendientes"], debito=r["debito"], credito=r["credito"],
                diferencia=r["diferencia"], guardado=datetime.now().isoformat(timespec="seconds"))


def _conservar_revisados(previos: list, nuevos: list) -> list:
    """El papel «revisado» guardado gana sobre su relectura (mismo id, o mismo tipo+número+foto de origen)."""
    clave = lambda d: (d.get("tipo"), str(d.get("numero", "")), d.get("origen", "")) if d.get("numero") else None
    por_id, por_clave = {d["id"]: d for d in previos}, {clave(d): d for d in previos if clave(d)}
    usados, out = set(), []
    for d in nuevos:
        p = por_id.get(d.get("id")) or por_clave.get(clave(d))
        if p is not None and p["id"] not in usados:   # un previo sustituye a una sola lectura nueva
            usados.add(p["id"]); out.append(p)
        else: out.append(d)
    return out + [p for p in previos if p["id"] not in usados]   # el revisado que la relectura no trae se conserva


# ── T10 · revisión de recibos dudosos (R8): listar, confirmar/editar → «revisado», recalcular el día, sumar a la referencia ──
RUTA_REF = DATOS / "referencia"
REV_ENTEROS = ("consumo", "propina", "domicilio", "descuento", "cortesia", "efectivo", "tarjeta", "transf", "credito", "subtotal", "pagado", "cambio")
REV_TEXTOS = {"medio": ("Efectivo", "Tarjeta", "Transferencia", "Crédito", "Mixto"), "hora": None, "detalle": None, "numero": None}
REV_TOPE = 500


@app.get("/api/contable/revision")
def cont_revision_listar():
    """Recibos de venta del libro por estado (por defecto «dudoso») con su recorte y motivos, entre `desde` y `hasta` (aaaa-mm-dd)."""
    desde, hasta = request.args.get("desde", ""), request.args.get("hasta", "9999-12-31")
    est = request.args.get("estado", "dudoso")
    if not ISO.match(desde) or not ISO.match(hasta): return jsonify(error="desde y hasta deben ser aaaa-mm-dd"), 400
    if est not in ("dudoso", "validado", "revisado"): return jsonify(error="estado desconocido"), 400
    out = []
    for dia in sorted(_leer_libro().values(), key=lambda x: x["fecha"]):
        if not desde <= dia["fecha"] <= hasta: continue
        for d in dia.get("documentos", []):
            if d.get("tipo") == "venta" and estado_de(d) == est:
                out.append(dict(fecha=dia["fecha"], id=d.get("id"), numero=d.get("numero", ""), estado=est, motivos=d.get("motivos") or d.get("avisos") or [],
                                recorte=d.get("recorte"), lectura=d.get("lectura"), documento=d))
    return jsonify(recibos=out[:REV_TOPE], total=len(out))


@app.post("/api/contable/revision/<fecha>/<doc_id>")
def cont_revision_confirmar(fecha, doc_id):
    """Confirma (cuerpo vacío) o edita (`cambios`: solo campos permitidos) un recibo → «revisado»; recalcula el día y lo agrega a la referencia."""
    if not ISO.match(fecha) or not re.fullmatch(r"[0-9a-f]{1,32}", doc_id): return jsonify(error="fecha o id inválidos"), 400
    if (request.content_length or 0) > 64 * 1024: return jsonify(error="Cuerpo demasiado grande"), 413
    j = request.get_json(silent=True)
    if j is None: j = {}
    cambios = j.get("cambios", {}) if isinstance(j, dict) else None
    if not isinstance(cambios, dict): return jsonify(error="cambios debe ser un objeto"), 400
    limpio = {}
    for k, v in cambios.items():
        if k in REV_ENTEROS:
            if isinstance(v, bool) or not isinstance(v, int) or not 0 <= v <= 10**9: return jsonify(error=f"{k}: entero entre 0 y 1000000000"), 400
        elif k in REV_TEXTOS:
            if not isinstance(v, str) or len(v) > 200 or (REV_TEXTOS[k] and v not in REV_TEXTOS[k]): return jsonify(error=f"{k}: valor inválido"), 400
        elif k == "fecha":
            if not isinstance(v, str) or not ISO.match(v): return jsonify(error="fecha: aaaa-mm-dd"), 400
        else: return jsonify(error=f"campo no editable: {k}"), 400
        limpio[k] = v
    with LOCK:
        lib = _leer_libro(); dia = lib.get(fecha)
        d = next((x for x in (dia or {}).get("documentos", []) if x.get("id") == doc_id and x.get("tipo") == "venta"), None)
        if d is None: return jsonify(error="No existe ese recibo en el libro"), 404
        b = _bloqueos(fecha, dia["documentos"])
        if b: return jsonify(error="R7: el día tiene compras de un documento soporte transmitido", bloqueos=b), 409
        d.update(limpio); d["estado"], d["motivos"], d["revisado"] = "revisado", [], True
        if d.get("avisos"): d["avisos_resueltos"], d["avisos"] = list(d.get("avisos_resueltos") or []) + d["avisos"], []   # FIX-13: el aviso viejo del OCR ya no cuenta
        r = construir_asientos(fecha, dia["documentos"], dia.get("banco", {}), _cont_cfg(), dia.get("cierre"))
        lib[fecha] = _dia(fecha, r, dia.get("banco", {}), dia.get("cierre")); _guardar_libro(lib)
        revisado = next(x for x in lib[fecha]["documentos"] if x.get("id") == doc_id)
        mes = str(revisado.get("fecha") or fecha)[:7]
        referencia.agregar(RUTA_REF / f"referencia_{mes}.json", mes, {**revisado, "fecha": revisado.get("fecha") or fecha})
    return jsonify(ok=True, diferencia=r["diferencia"], estado="revisado")


@app.get("/api/contable/crudo")
def cont_crudo():
    """ADR-004: lo leído (documentos, banco, cierre) de los días del rango, para importarlo en un PC sin OCR (T19)."""
    d, h = request.args.get("desde", ""), request.args.get("hasta", "")
    if any(x and not ISO.match(x) for x in (d, h)): return jsonify(error="Fecha inválida"), 400
    lib = _leer_libro()
    if not any((not d or k >= d) and (not h or k <= h) for k in lib): return jsonify(error="No hay días en ese rango"), 404
    return send_file(io.BytesIO(crudo_json(lib, d, h)), mimetype="application/json", as_attachment=True,
                     download_name=f"ingresos_crudo_{d or 'inicio'}_{h or 'fin'}.json")


@app.post("/api/contable/crudo")
def cont_importar():
    """ADR-004 (T19): importa un archivo crudo día por día. Nuevo → entra; igual → se omite; distinto → conflicto (no se toca salvo que
    venga en `reemplazar`); con compras de un DS transmitido → bloqueado (R7); inválido → no entra y sale con el motivo (R10).
    Cada día se recalcula con la config de este PC (ADR-002) y todo se guarda en una sola escritura de libro.json."""
    f = request.files.get("archivo")
    if not f: return jsonify(error="No llegó ningún archivo"), 400
    try: dias, invalidos = leer_crudo(f.read())
    except CrudoInvalido as e: return jsonify(error=str(e)), 400
    reemplazar = {x.strip() for x in request.form.get("reemplazar", "").split(",") if x.strip()}
    inf = dict(nuevos=[], iguales=[], conflictos=[], bloqueados=[], reemplazados=[], invalidos=invalidos)
    leido = lambda d: (d.get("documentos", []), d.get("banco") or {}, d.get("cierre") or {})
    with LOCK:
        lib, cfg, cambio = _leer_libro(), _cont_cfg(), False
        for d in dias:
            fecha = d["fecha"]; previo = lib.get(fecha)
            if previo is not None and leido(previo) == leido(d): inf["iguales"].append(fecha); continue
            try: r = construir_asientos(fecha, copy.deepcopy(d["documentos"]), d["banco"], cfg, d["cierre"])
            except Exception as e:  # noqa: BLE001  un documento que el cálculo no entiende: el día no entra y se dice por qué
                inf["invalidos"].append(dict(fecha=fecha, motivo=f"no se pudo calcular: {str(e)[:120]}")); continue
            if previo is not None:
                b = _bloqueos(fecha, r["documentos"])
                if b: inf["bloqueados"].append(dict(fecha=fecha, motivos=b)); continue
                if fecha not in reemplazar:
                    inf["conflictos"].append(dict(fecha=fecha, papeles_actuales=len(previo.get("documentos", [])), papeles_archivo=len(d["documentos"]))); continue
            lib[fecha] = dict(fecha=fecha, documentos=r["documentos"], banco=d["banco"], cierre=d["cierre"], cruces=r["cruces"], filas=r["filas"], pendientes=r["pendientes"],
                              debito=r["debito"], credito=r["credito"], diferencia=r["diferencia"], guardado=d["guardado"] or datetime.now().isoformat(timespec="seconds"),
                              importado=datetime.now().isoformat(timespec="seconds"))
            inf["reemplazados" if previo is not None else "nuevos"].append(fecha); cambio = True
        if cambio: _guardar_libro(lib)
    return jsonify(ok=True, **inf)


@app.delete("/api/contable/libro/<fecha>")
def cont_borrar(fecha):
    with LOCK:
        b = _bloqueos(fecha, [])
        if b: return jsonify(error="R7: el día tiene compras de un documento soporte transmitido", bloqueos=b), 409
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
    """T1 de 03: otra página web no puede hacer POST/DELETE a localhost (CSRF). FIX-10: el Host se revisa en todo método,
    así una página por DNS rebinding tampoco lee proveedores (cédulas, direcciones) ni el Excel con GET."""
    if "@" in request.host or urlsplit("//" + request.host).hostname not in {"127.0.0.1", "localhost", "::1"}:   # M-3: user@host no pasa aunque Werkzeug cambie
        return jsonify(error="Host no permitido"), 403
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
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
                total=d.total, estado=d.estado, motivo=d.motivo, cuds=d.cuds, fecha_limite=d.fecha_limite, lineas=[asdict(l) for l in d.lineas],
                clase=d.clase, ajusta_a=d.ajusta_a or None, concepto=d.concepto)


def _grupo_json(g) -> dict:
    return dict(documentado=g.documentado or None, proveedor_id=g.proveedor.id if g.proveedor else None, tercero=g.tercero, semana=g.semana, lunes=g.lunes, domingo=g.domingo,
                total=g.total, fecha_limite=g.fecha_limite, estado=g.estado, dias_restantes=g.dias_restantes, registrado=g.proveedor is not None,
                elegir=g.elegir, avisos=g.avisos, compras=[asdict(c) for c in g.compras])


def _bloqueos(fecha: str, docs: list) -> list[str]:
    """R7: lo transmitido no cambia. Sin soporte.db no hay nada transmitido (no se crea la base solo por guardar un día)."""
    if not RUTA_SOPORTE.exists(): return []
    con = _sop_con()
    try: return soporte.bloqueos(con, fecha, docs)
    finally: con.close()


@app.get("/api/soporte/documentos")
def sop_documentos():
    con = _sop_con()
    try:
        try: return jsonify(documentos=[_doc_json(d) for d in soporte.documentos(con, _sop_cfg())])
        except ValueError as e: return jsonify(error=f"contable.json: {e}"), 400
    finally: con.close()


@app.post("/api/soporte/<int:doc_id>/transmitido")
def sop_transmitido(doc_id):
    j = request.get_json(silent=True) or {}
    cuds = j.get("cuds") or ""
    if not isinstance(cuds, str) or len(cuds) > 200: return jsonify(error="CUDS inválido"), 400
    with LOCK:
        con = _sop_con()
        try: soporte.marcar_transmitido(con, doc_id, cuds)
        except soporte.NoSePuede as e: return jsonify(error=str(e)), 409
        finally: con.close()
    return jsonify(ok=True)


@app.post("/api/soporte/<int:doc_id>/anular")
def sop_anular(doc_id):
    j = request.get_json(silent=True) or {}
    motivo = j.get("motivo")
    if not isinstance(motivo, str): return jsonify(error="Escriba el motivo de la anulación"), 400
    with LOCK:
        con = _sop_con()
        try: soporte.anular(con, doc_id, motivo)
        except soporte.NoSePuede as e: return jsonify(error=str(e)), 409
        finally: con.close()
    return jsonify(ok=True)


@app.post("/api/soporte/<int:doc_id>/ajuste")
def sop_ajuste(doc_id):
    """R8: nota de ajuste sobre un documento transmitido. Cuerpo: {concepto, lineas: [{descripcion, valor}]}; la validación vive en soporte.py."""
    j = request.get_json(silent=True) or {}
    if not isinstance(j, dict): return jsonify(error="Cuerpo inválido"), 400
    with LOCK:
        con = _sop_con()
        try: d = soporte.nota_ajuste(con, doc_id, j.get("lineas"), j.get("concepto"), _sop_cfg())
        except soporte.NoSePuede as e: return jsonify(error=str(e)), 409
        except ValueError as e: return jsonify(error=f"contable.json: {e}"), 400
        except soporte_db.RangoAgotado as e: return jsonify(error=str(e)), 409
        finally: con.close()
    return jsonify(ok=True, documento=_doc_json(d))


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
            for x in sel:   # lo no documentado de la semana primero; si todo está documentado, generar responde R3 (FIX-7)
                g = next((g for g in sorted(gs, key=lambda g: bool(g.documentado)) if g.semana == x.get("semana")
                          and ((g.proveedor and g.proveedor.id == x.get("proveedor_id"))
                               or (not g.proveedor and x.get("proveedor_id") is None and g.tercero == x.get("tercero")))), None)
                if g is None: return jsonify(error=f"No existe la semana {x.get('semana')!s:.20} de ese proveedor"), 400
                elegidos.append(g)
            try: docs = soporte.generar(con, elegidos, bool(j.get("confirmar_vencidos")))
            except soporte.NoSeGenera as e: return jsonify(error=str(e)), 409
            except soporte_db.RangoAgotado as e: return jsonify(error=str(e)), 409
            return jsonify(documentos=[_doc_json(d) for d in docs])
        finally: con.close()


MEDIOS_COMPRA = ("Efectivo", "Transferencia", "Nequi", "Daviplata", "QR", "Bre-B", "Tarjeta", "PSE", "Crédito personal")


@app.post("/api/soporte/compra")
def sop_compra():
    """R4: compra que el OCR no tiene (p. ej. pagada por transferencia). Se guarda en libro.json como factura con origen «manual»
    en el día de su fecha, así sale en DATOS OCR, en el libro y en las semanas: una sola fuente de compras (03 §5, N2)."""
    j = request.get_json(silent=True)
    if not isinstance(j, dict): return jsonify(error="Falta la compra"), 400
    fecha, tercero, desc, medio = (str(j.get(k) or "").strip() for k in ("fecha", "tercero", "descripcion", "medio"))
    try: valor = int(j.get("valor"))   # valor_compra_pesos: total pagado al proveedor (art. 4 Res. 167/2021, valor de la operación)
    except (TypeError, ValueError): valor = 0
    try: date.fromisoformat(fecha); fok = bool(ISO.match(fecha))
    except ValueError: fok = False
    error = ("Fecha inválida" if not fok else "Falta el proveedor" if not tercero or provs.es_encabezado(tercero) else "Proveedor demasiado largo" if len(tercero) > 200
             else "Falta la descripción" if not desc else "Descripción demasiado larga (máx. 200)" if len(desc) > 200
             else "El valor debe ser un número entre 1 y 10.000.000.000" if not 0 < valor <= 10**10 else "Medio de pago desconocido" if medio not in MEDIOS_COMPRA else "")
    if error: return jsonify(error=error), 400
    d = {**_base_doc("factura", ""), "fecha": fecha, "tercero": tercero, "detalle": desc, "descripcion": desc, "valor": valor, "medio": medio, "origen": "manual"}
    r = CLASIF.clasificar(tercero, desc, "")
    d["cuenta"], d["conf"], d["motivo"] = r["cuenta"], r["conf"], r["motivo"]
    with LOCK:
        lib = _leer_libro(); dia = lib.get(fecha) or dict(fecha=fecha, banco={}, cierre={})
        r = construir_asientos(fecha, dia.get("documentos", []) + [d], dia.get("banco", {}), _cont_cfg(), dia.get("cierre"))
        lib[fecha] = {**dia, "documentos": r["documentos"], "cruces": r["cruces"], "filas": r["filas"], "pendientes": r["pendientes"], "debito": r["debito"],
                      "credito": r["credito"], "diferencia": r["diferencia"], "guardado": datetime.now().isoformat(timespec="seconds")}   # recalculado: sin aviso de FIX-6
        _guardar_libro(lib)
    return jsonify(ok=True, documento=d)


@app.get("/api/soporte/excel")
def sop_excel():
    try: ids = [int(x) for x in request.args["ids"].split(",") if x] if request.args.get("ids") else None
    except ValueError: return jsonify(error="ids inválidos"), 400
    con = _sop_con()
    try:
        try: docs = soporte.documentos(con, _sop_cfg(), ids)
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
