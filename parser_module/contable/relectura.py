"""C5 · ADR-005: leer un recorte, validarlo y releer con variantes solo lo dudoso. R2, R4, R7, N2, N4.

motor: función Image → texto (un `.nombre` opcional se anota en cada candidato). Ollama atiende uno a la vez: toda llamada pasa por MOTOR_LOCK.
Voto: el primer candidato que valida entero gana; si ninguno, cada campo toma el valor más repetido (empate → V0) y el recibo queda «dudoso».
Foto borrosa (laplaciano < umbral): aunque valide, se relee hasta que una segunda variante coincida en todos los campos.
"""
from __future__ import annotations
import json, threading, time
from collections import Counter
from ocr_module.preprocess import nitidez, variantes
from .documentos import parse_venta
from .validar import validar
from . import recortes

# umbral_laplaciano: sin calibrar (T9 lo fija con N3); 100 sobre ≤1000 px es la regla usual de «borrosa».
CONFIG = {"max_relecturas": 3, "umbral_laplaciano": 100.0}
MOTOR_LOCK = threading.Lock()
CAMPOS = ("numero", "hora", "detalle", "medio", "items", "subtotal", "descuento", "consumo", "domicilio", "propina",
          "pagado", "cambio", "efectivo", "tarjeta", "transf", "credito", "cortesia")
TIEMPO_AGOTADO = "Tiempo agotado: quedaron relecturas sin hacer"
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
                umbral=None, reloj=time.monotonic) -> dict:
    """Recorte (PIL) → documento con `estado`, `motivos`, `lectura` y, si hay `carpeta`, el nombre del `recorte` guardado.
    limite_s: tope de segundos para este recorte; al pasarlo no se relee más y, si no validó, queda «dudoso» por tiempo."""
    max_relecturas = CONFIG["max_relecturas"] if max_relecturas is None else max(0, min(int(max_relecturas), 3))
    umbral = CONFIG["umbral_laplaciano"] if umbral is None else umbral
    parsear = parsear or parse_venta
    nombre_motor = getattr(motor, "nombre", "local")
    t0 = reloj(); nit = nitidez(recorte); borrosa = nit["laplaciano"] < umbral
    cands, pasadas, agotado = [], [], False
    ganador = None
    for i, (var, img) in enumerate(variantes(recorte)[:1 + max_relecturas]):
        if i and limite_s is not None and reloj() - t0 >= limite_s: agotado = True; break
        t = reloj()
        try:
            with MOTOR_LOCK: texto = motor(img)
        except Exception as e:  # noqa: BLE001
            if not i: raise                     # sin la primera lectura no hay recibo: el error sube como hoy
            pasadas.append(dict(variante=var, segundos=round(reloj() - t, 2), error=str(e))); break
        doc = parsear(texto); mot = validar(doc, ctx)
        cands.append(dict(variante=var, doc=doc, motivos=mot))
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
        doc = _votar(cands); motivos = validar(doc, ctx) or list(cands[0]["motivos"])
    if agotado and not ganador: motivos.append(TIEMPO_AGOTADO)
    doc["avisos"] = list(doc.get("avisos") or []) + (["Foto borrosa"] if borrosa else [])
    doc["estado"] = "dudoso" if motivos else "validado"
    doc["motivos"] = motivos
    doc["lectura"] = dict(
        pasadas=pasadas, nitidez=round(nit["laplaciano"], 1), tenengrad=round(nit["tenengrad"], 1), borrosa=borrosa,
        segundos=round(reloj() - t0, 2),
        candidatos={k: [dict(valor=c["doc"].get(k), variante=c["variante"], motor=nombre_motor) for c in cands] for k in CAMPOS})
    if carpeta is not None: doc["recorte"] = recortes.guardar(recorte, carpeta)
    return doc
