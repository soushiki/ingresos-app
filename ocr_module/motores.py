"""C3 · fachada de motores (ADR-017). Indra si puede; si no, Tesseract como en v1.6.0.
Una llamada que falla usa Tesseract solo para esa foto; con 2 fallas seguidas indra.py queda apagado y todo va con Tesseract.
Mismas firmas que las de hoy: leer_digitos(img) -> set|None (como digitos.numeros_tesseract) y
detectar_giro(img) -> (giro, confianza, inclinacion) (ADR-018)."""
from __future__ import annotations
from . import digitos, indra, orientacion


def leer_digitos(img):
    """Conjunto de enteros que ve el motor activo. El texto de Indra pasa por digitos._enteros."""
    try:
        return digitos._enteros(indra.cliente().pedir("numeros", img)["texto"])
    except indra.IndraNoDisponible:
        return digitos.numeros_tesseract(img)


def detectar_giro(img):
    """(grados horario, confianza, inclinación en grados). Indra: confianza 1.0 con inclinación; Tesseract: inclinación 0.0."""
    try:
        r = indra.cliente().pedir("upright", img)
        return int(r["giro"]), 1.0, float(r["incl"])
    except indra.IndraNoDisponible:
        giro, conf = orientacion.giro_automatico(img)
        return giro, conf, 0.0


def estado():
    """{'motor': 'indra'|'tesseract', 'motivo': str|None, 'aviso': str|None} para /api/contable/capacidades."""
    e = dict(indra.cliente().estado())
    if e["motor"] == "indra":
        e["aviso"] = None
    elif e["motivo"] == "sin venv":
        e["aviso"] = "Indra no disponible: se usa Tesseract"
    else:
        e["aviso"] = f"Indra caído ({e['motivo']}): se usa Tesseract"
    return e
