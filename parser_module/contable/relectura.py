"""C5 · ADR-005: leer un recorte, validarlo y releer con variantes solo lo dudoso. R2, R4, R7, N2, N4.

motor: función Image → texto (un `.nombre` opcional se anota en cada candidato). Ollama atiende uno a la vez: toda llamada pasa por MOTOR_LOCK.
Voto: el primer candidato que valida entero gana; si ninguno, cada campo toma el valor más repetido (empate → V0) y el recibo queda «dudoso».
Foto borrosa (laplaciano < umbral): aunque valide, se relee hasta que una segunda variante coincida en todos los campos.
"""
from __future__ import annotations
import json, threading, time
from collections import Counter
from ocr_module.preprocess import nitidez, variante
from .documentos import MARCA, leer_texto, parse_venta
from .validar import FALTA, cruces, faltantes, notas_digitos, numeros_de_nombre, validar
from . import recortes

# umbral_laplaciano: sin calibrar (T9 lo fija con N3); 100 sobre ≤1000 px es la regla usual de «borrosa».
# variantes: orden de las pasadas, medido en T9 (20 fotos con más dudosos, 107 recibos; recibos enteros bien: V0 59, y lo que cada
# una suma a lo ya cubierto: V4 +9, V3 +4, V1 +1, V2 +0). V4 (Real-ESRGAN) nunca va sola; sin ejecutable se salta y entra V2.
CONFIG = {"max_relecturas": 3, "umbral_laplaciano": 100.0, "variantes": ["V0", "V4", "V3", "V1", "V2"]}


def _pasadas(recorte, n):
    """Las primeras n variantes de CONFIG, calculadas solo cuando hacen falta; una que no está (V4 sin ejecutable) se salta."""
    for var in CONFIG["variantes"]:
        if n <= 0: return
        img = variante(recorte, var)
        if img is not None: n -= 1; yield var, img
MOTOR_LOCK = threading.Lock()
CAMPOS = ("numero", "hora", "detalle", "medio", "items", "subtotal", "descuento", "consumo", "domicilio", "propina",
          "pagado", "cambio", "efectivo", "tarjeta", "transf", "credito", "cortesia")
TIEMPO_AGOTADO = "Tiempo agotado: quedaron relecturas sin hacer"
SIN_CANDIDATO = "Ninguna lectura validó entera: el voto por campo cuadra pero hay que revisarlo"
BORROSA_SIN_PAR = "Foto borrosa: ninguna segunda lectura coincide"


def _clave(v):
    return json.dumps(v, sort_keys=True, ensure_ascii=False)


def _iguales(a: dict, b: dict) -> bool:
    return all(_clave(a.get(k)) == _clave(b.get(k)) for k in CAMPOS)


def _votar(cands: list) -> dict:
    """Cada campo toma el valor más repetido entre las pasadas; empate → el de la primera pasada (V0)."""
    out = dict(cands[0]["doc"])
    for k in CAMPOS:
        cuenta = Counter(_clave(c["doc"].get(k)) for c in cands)
        mejor = max(cuenta.values())
        out[k] = next(c["doc"].get(k) for c in cands if cuenta[_clave(c["doc"].get(k))] == mejor)
    return out


def leer_recibo(recorte, motor, ctx=None, max_relecturas=None, limite_s=None, *, carpeta=None, parsear=None,
                umbral=None, reloj=time.monotonic, leer_digitos=None) -> dict:
    """Recorte (PIL) → documento con `estado`, `motivos`, `lectura` y, si hay `carpeta`, el nombre del `recorte` guardado.
    leer_digitos: imagen → set de enteros (ocr_module.digitos.numeros_tesseract) o None; se calcula en cada pasada con SU imagen
    y va a ctx["digitos"] (R3b: otro número del nombre → motivo; no verlo → doc["notas"], sin marcar dudoso). ctx["catalogo"] (R6) lo pone quien llama. Sin leer_digitos nada cambia.
    limite_s: tope de segundos para este recorte; al pasarlo no se relee más y, si no validó, queda «dudoso» por tiempo."""
    max_relecturas = CONFIG["max_relecturas"] if max_relecturas is None else max(0, min(int(max_relecturas), 3))
    umbral = CONFIG["umbral_laplaciano"] if umbral is None else umbral
    parsear = parsear or parse_venta
    nombre_motor = getattr(motor, "nombre", "local")
    t0 = reloj(); nit = nitidez(recorte); borrosa = nit["laplaciano"] < umbral
    cands, pasadas, agotado, dig0 = [], [], False, None
    ganador = None
    for i, (var, img) in enumerate(_pasadas(recorte, 1 + max_relecturas)):
        if i and limite_s is not None and reloj() - t0 >= limite_s: agotado = True; break
        t = reloj()
        try:
            with MOTOR_LOCK: texto = motor(img)
        except Exception as e:  # noqa: BLE001
            if not i: raise                     # sin la primera lectura no hay recibo: el error sube como hoy
            pasadas.append(dict(variante=var, segundos=round(reloj() - t, 2), error=str(e))); break
        dig = leer_digitos(img) if leer_digitos else None
        if not i: dig0 = dig
        doc = parsear(texto); mot = validar(doc, dict(ctx or {}, digitos=dig) if dig is not None else ctx)
        cands.append(dict(variante=var, doc=doc, motivos=mot, dig=dig))
        pasadas.append(dict(variante=var, segundos=round(reloj() - t, 2), motivos=mot))
        validos = [c for c in cands if not c["motivos"]]
        if not borrosa and validos: ganador = validos[0]; break
        par = next((a for j, a in enumerate(validos) for b in validos[j + 1:] if _iguales(a["doc"], b["doc"])), None)
        if par: ganador = par; break
    validos = [c for c in cands if not c["motivos"]]
    if ganador:
        doc, motivos = dict(ganador["doc"]), []
    elif validos:                               # borrosa: validó pero sin segunda lectura que coincida
        doc, motivos = dict(validos[0]["doc"]), [BORROSA_SIN_PAR]
    else:
        doc = _votar(cands); motivos = validar(doc, dict(ctx or {}, digitos=dig0) if dig0 is not None else ctx) or [SIN_CANDIDATO]
    if agotado and not ganador: motivos.append(TIEMPO_AGOTADO)
    doc["avisos"] = list(doc.get("avisos") or []) + (["Foto borrosa"] if borrosa else [])
    doc["estado"] = "dudoso" if motivos else "validado"
    doc["motivos"] = motivos
    visto = (ganador or (validos[0] if validos else None) or {}).get("dig", dig0)   # R3b: nota suave del lector que respalda al documento
    doc["notas"] = notas_digitos(doc, dict(ctx or {}, digitos=visto))
    doc["lectura"] = dict(
        pasadas=pasadas, nitidez=round(nit["laplaciano"], 1), tenengrad=round(nit["tenengrad"], 1), borrosa=borrosa,
        segundos=round(reloj() - t0, 2),
        candidatos={k: [dict(valor=c["doc"].get(k), variante=c["variante"], motor=nombre_motor) for c in cands] for k in CAMPOS})
    if carpeta is not None: doc["recorte"] = recortes.guardar(recorte, carpeta)
    return doc


def _v0(motor, img, reloj):
    t = reloj()
    with MOTOR_LOCK: texto = motor(img)
    return texto, round(reloj() - t, 2)


def _con_v0(motor, texto):
    """El motor de leer_recibo: la primera llamada (V0) ya se hizo; las relecturas sí van al motor."""
    hecho = []
    def leer(img):
        if not hecho: hecho.append(1); return texto
        return motor(img)
    leer.nombre = getattr(motor, "nombre", "local"); return leer


def _nums(docs) -> set:
    return {int(d["numero"]) for d in docs if d.get("tipo") == "venta" and str(d.get("numero") or "").isdigit()}


def leer_hoja(trozos, motor, categoria="", nombre="", *, completa=True, carpeta=None, separar=None, factor_tope=3.0,
              tope_s=None, umbral=None, reloj=time.monotonic, catalogo=None, leer_digitos=None) -> dict:
    """C7 · Los recortes de una hoja → documentos. R5, R2, N2.
    1) V0 de cada recorte (lo de siempre) mide T. 2) Un recorte con UNA venta pasa por leer_recibo con los números del nombre
    de la foto; los demás (cierres, gastos, varios papeles pegados en un texto) siguen como hoy y la venta solo se valida.
    3) Si falta un número del nombre (`completa`: la foto es todo el lote), se re-segmenta cada recorte una vez y se relee
       lo que se parta, si trae un faltante. 4) Montos idénticos entre vecinos → «dudoso».
    Tope: factor_tope × T para toda la hoja (o `tope_s` segundos); al pasarlo no se relee más (leer_recibo marca «tiempo agotado»)."""
    esperados = numeros_de_nombre(nombre) if categoria in ("", "comandas") else None
    ctx = {k: v for k, v in (("esperados", esperados), ("catalogo", catalogo)) if v} or None
    t0 = reloj(); v0 = [_v0(motor, t, reloj) for t in trozos]
    tope = t0 + (factor_tope * (reloj() - t0) if tope_s is None else tope_s)

    def un_trozo(img, texto, seg):
        docs = leer_texto(texto, categoria)
        if len(docs) == 1 and docs[0]["tipo"] == "venta":
            extra = [a for a in docs[0]["avisos"] if a not in parse_venta(texto)["avisos"]]   # p. ej. «lo subiste como comandas…»
            d = leer_recibo(img, _con_v0(motor, texto), ctx, limite_s=max(0.0, tope - reloj()), carpeta=carpeta, umbral=umbral, reloj=reloj,
                           leer_digitos=leer_digitos)
            d["avisos"] = extra + d["avisos"]
            d["lectura"]["pasadas"][0]["segundos"] = seg; d["lectura"]["segundos"] = round(d["lectura"]["segundos"] + seg, 2)
            return [d], d["texto"]
        ventas = [d for d in docs if d["tipo"] == "venta"]
        nombre_rec = recortes.guardar(img, carpeta) if carpeta is not None and ventas else None
        for d in ventas:
            d["motivos"] = validar(d, ctx); d["estado"] = "dudoso" if d["motivos"] else "validado"
            if nombre_rec: d["recorte"] = nombre_rec
        return docs, texto

    grupos = [un_trozo(img, *v) for img, v in zip(trozos, v0)]
    todos = lambda: [d for g, _ in grupos for d in g]
    falta = faltantes(todos(), esperados) if esperados and completa and _nums(todos()) else []
    if falta and separar:
        for i, img in enumerate(trozos):
            if not falta or reloj() >= tope: break
            partes = separar(img)
            if len(partes) < 2: continue
            nuevos = [un_trozo(p, *_v0(motor, p, reloj)) for p in partes]
            docs = [d for g, _ in nuevos for d in g]
            if (_nums(docs) - _nums(grupos[i][0])) & set(falta):
                grupos[i] = (docs, f"\n{MARCA}\n".join(t for _, t in nuevos)); falta = faltantes(todos(), esperados)
    ventas = [d for d in todos() if d["tipo"] == "venta"]
    for d in ventas:
        c = cruces(d, ventas)
        if c: d["motivos"] = list(d.get("motivos") or []) + c; d["estado"] = "dudoso"
    avisos = [FALTA.format(n) for n in falta]
    if avisos and ventas: ventas[0]["avisos"] = list(ventas[0]["avisos"]) + avisos
    return dict(documentos=todos(), texto=f"\n{MARCA}\n".join(t for _, t in grupos), segundos=round(reloj() - t0, 2), avisos=avisos)
