"""R9 / ADR-007: la referencia es una COPIA CONGELADA de los recibos corregidos; medir nunca escribe el libro.
`congelar` lee el libro (solo lectura) y escribe `referencia_<mes>.json`; `medir` relee las fotos con un lector inyectable
y devuelve el informe (el llamador lo guarda en `informes/`). Aquí no hay ninguna escritura sobre libro.json."""
from __future__ import annotations
import hashlib, json, re
from datetime import datetime
from pathlib import Path
from .asientos import estado_de
from . import recortes

# campos que se comparan contra la referencia (los que mueven asientos)
CAMPOS = ("fecha", "consumo", "propina", "domicilio", "descuento", "cortesia", "efectivo", "tarjeta", "transf", "credito", "medio")


def huella(ruta) -> str:
    """sha256 del archivo (o «» si no existe): sirve para probar que medir no tocó el libro."""
    p = Path(ruta)
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else ""


def _foto_de(origen: str) -> tuple:
    """«carpeta/hoja.jpg#2» → («carpeta/hoja.jpg», 2). Sin «#n» la página es 1."""
    base, _, pg = (origen or "").partition("#")
    return base, int(pg) if pg.isdigit() else 1


def congelar(ruta_libro, mes: str, destino) -> dict:
    """Copia los recibos de venta revisados del mes (aaaa-mm) a `destino`. Solo LEE el libro."""
    libro = json.loads(Path(ruta_libro).read_text(encoding="utf-8"))
    docs = []
    for dia in sorted(libro):
        for d in libro[dia].get("documentos", []):
            if d.get("tipo") != "venta" or estado_de(d) != "revisado" or not str(d.get("fecha", "")).startswith(mes): continue
            foto, pagina = _foto_de(d.get("origen", ""))
            docs.append({"numero": str(d.get("numero", "")), "foto": foto, "pagina": pagina, "documento": d})
    ref = {"mes": mes, "congelado": datetime.now().isoformat(timespec="seconds"), "documentos": docs}
    destino = Path(destino); destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(ref, ensure_ascii=False, indent=1), encoding="utf-8")
    return ref


def agregar(destino, mes: str, doc: dict) -> dict:
    """T10: suma un recibo recién «revisado» a la referencia del mes (la crea si no existe); mismo número y foto → lo reemplaza; sin número → por id."""
    destino = Path(destino)
    try: ref = json.loads(destino.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError): ref = {"mes": mes, "congelado": datetime.now().isoformat(timespec="seconds"), "documentos": []}
    foto, pagina = _foto_de(doc.get("origen", "")); numero = str(doc.get("numero", ""))
    ref["documentos"] = [r for r in ref["documentos"] if not ((numero and r["numero"] == numero and r["foto"] == foto and r["pagina"] == pagina)
                                                  or (not numero and doc.get("id") and r["documento"].get("id") == doc["id"]))]
    ref["documentos"].append({"numero": numero, "foto": foto, "pagina": pagina, "documento": doc})
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_suffix(".tmp"); tmp.write_text(json.dumps(ref, ensure_ascii=False, indent=1), encoding="utf-8"); tmp.replace(destino)
    return ref


def exportar_entrenamiento(ref: dict, carpeta_recortes, destino) -> dict:
    """T15 · R10: por cada recibo de la referencia con recorte en disco escribe `<numero>_<huella>.jpg` + `.json` (el documento corregido)
    en `destino`: pares imagen/etiqueta para entrenar o afinar un lector. Sin recorte → se cuenta en `sin_recorte` y no se exporta."""
    destino = Path(destino); destino.mkdir(parents=True, exist_ok=True)
    n, sin = 0, []
    for r in ref["documentos"]:
        d = r["documento"]; datos = recortes.abrir(d.get("recorte"), carpeta_recortes)
        if datos is None: sin.append(r["numero"]); continue
        base = f"{re.sub(r'[^0-9A-Za-z_-]', '_', r['numero']) or 'sn'}_{d['recorte'][:-4]}"
        (destino / f"{base}.jpg").write_bytes(datos)
        (destino / f"{base}.json").write_text(json.dumps({"imagen": f"{base}.jpg", "foto": r["foto"], "pagina": r["pagina"], "documento": d}, ensure_ascii=False, indent=1), encoding="utf-8")
        n += 1
    return {"exportados": n, "sin_recorte": sin}


def _valor(d, c): return d.get(c, "" if c in ("fecha", "medio") else 0)


def medir(ref: dict, carpeta_fotos, leer_hoja, leer_texto) -> dict:
    """Relee cada foto de la referencia (V0, sin relectura) y compara por número de recibo.
    leer_hoja(ruta, pagina) → texto; leer_texto(texto, categoria) → documentos. Sin libro: no recibe ni escribe nada de él.
    omitido = el número no aparece (o la foto no se pudo leer). validado = estado distinto de «dudoso»; «validado con error» = validado y algún campo distinto."""
    carpeta = Path(carpeta_fotos)
    por_foto = {}
    for r in ref["documentos"]: por_foto.setdefault((r["foto"], r["pagina"]), []).append(r)
    campos = {c: {"ok": 0, "mal": 0} for c in CAMPOS}
    omitidos, dudosos, con_error, errores_lectura, detalle = [], [], [], [], []
    for (foto, pagina), recs in por_foto.items():
        try:
            leidos = {str(d.get("numero", "")): d for d in leer_texto(leer_hoja(carpeta / foto, pagina), "comandas") if d.get("tipo") == "venta"}
        except Exception as e:  # noqa: BLE001  una foto mala no tumba la medición
            leidos = {}; errores_lectura.append({"foto": foto, "error": str(e)})
        for r in recs:
            n, esp = r["numero"], r["documento"]; got = leidos.get(n)
            if got is None: omitidos.append(n); continue
            malos = [c for c in CAMPOS if _valor(got, c) != _valor(esp, c)]
            for c in CAMPOS: campos[c]["mal" if c in malos else "ok"] += 1
            dudoso = estado_de(got) == "dudoso"   # por estado, no por avisos: «Foto borrosa» en un validado no es dudoso
            if dudoso: dudosos.append(n)
            elif malos: con_error.append(n)
            if malos: detalle.append({"numero": n, "dudoso": dudoso, "campos": {c: {"esperado": _valor(esp, c), "leido": _valor(got, c)} for c in malos}})
    total = len(ref["documentos"]); leidos_n = total - len(omitidos)
    return {"mes": ref.get("mes"), "fecha_informe": datetime.now().isoformat(timespec="seconds"), "variante": "V0", "total": total,
            "leidos": leidos_n, "omitidos": len(omitidos), "omitidos_numeros": omitidos, "dudosos": len(dudosos), "dudosos_numeros": dudosos,
            "validados_con_error": len(con_error), "validados_con_error_numeros": con_error,
            "por_campo": {c: {**v, "acierto": round(v["ok"] / (v["ok"] + v["mal"]), 4) if v["ok"] + v["mal"] else None} for c, v in campos.items()},
            "errores_lectura": errores_lectura, "detalle": detalle}
