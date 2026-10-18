"""M-13 · ADR-008: recibos faltantes como documentos marcador (tipo "faltante") dentro del día. Puro, sin E/S.
Un marcador no cuenta (contar False) y asientos/medir lo ignoran porque solo miran tipo == "venta"."""
from __future__ import annotations
import uuid

MOTIVO_MAX = 200


def crear(numeros, origen, fecha, recorte, nombre_entendido=True) -> list[dict]:
    """Un marcador por número faltante; si el nombre de la foto no se entiende, uno solo sin número."""
    def marca(numero, aviso):
        return dict(id=uuid.uuid4().hex[:8], tipo="faltante", numero=numero, origen=origen, fecha=fecha, recorte=recorte,
                    estado="falta", motivo="", contar=False, avisos=[aviso])
    if not nombre_entendido:
        return [marca("", f"No entiendo el nombre de la foto {origen}")]
    return [marca(str(int(n)), f"Falta el recibo {int(n)} en esta foto") for n in numeros]


def anotar(doc, campos) -> dict:
    """El marcador abierto pasa a venta manual revisada (mismo id), con de_foto = su origen viejo."""
    if doc.get("tipo") != "faltante" or doc.get("estado") != "falta": raise ValueError("solo se anota un faltante abierto")
    nuevo = {**doc, **(campos or {})}
    nuevo.update(tipo="venta", origen="manual", de_foto=doc.get("origen", ""), estado="revisado", revisado=True, contar=True, avisos=[])
    if not nuevo.get("numero"): nuevo["numero"] = doc.get("numero", "")
    return nuevo


def cerrar(doc, motivo) -> dict:
    """Marca «no existe» con su motivo (≤ 200); sigue sin contar y queda como rastro."""
    if doc.get("tipo") != "faltante" or doc.get("estado") != "falta": raise ValueError("solo se cierra un faltante abierto")
    motivo = str(motivo or "").strip()
    if len(motivo) > MOTIVO_MAX: raise ValueError(f"motivo de más de {MOTIVO_MAX} caracteres")
    return {**doc, "estado": "no_existe", "motivo": motivo, "contar": False}


def abiertos(docs) -> list[dict]:
    return [d for d in docs if d.get("tipo") == "faltante" and d.get("estado") == "falta"]


def reconciliar(previos, nuevos) -> list[dict]:
    """`nuevos` sin los marcadores ya resueltos: anotados (venta manual con de_foto == origen y mismo número) o no_existe."""
    resueltos = set()
    for p in previos:
        if p.get("tipo") == "faltante" and p.get("estado") == "no_existe": resueltos.add((p.get("origen"), p.get("numero")))
        elif p.get("tipo") == "venta" and p.get("origen") == "manual" and p.get("de_foto"): resueltos.add((p["de_foto"], p.get("numero")))
    return [n for n in nuevos if not (n.get("tipo") == "faltante" and (n.get("origen"), n.get("numero")) in resueltos)]
