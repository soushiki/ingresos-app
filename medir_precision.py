"""R9 / ADR-007: precisión del lector contra la referencia congelada. NUNCA escribe libro.json; solo la referencia y el informe.
    python medir_precision.py --mes 2026-09 --fotos "D:/ruta/a/las/fotos" [--motor local] [--refrescar] [--variantes V0,V1,V2,V3,V4]
T9: con --variantes mide cada variante por separado (la imagen de cada papel pasa por esa variante antes del OCR) y deja un
informe por variante + una comparación. V4 (Real-ESRGAN) se salta si no está el ejecutable."""
import argparse, io, json, sys
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATOS = BASE / "datos"


def leer_hoja_v0(ruta: Path, pagina: int, motor, variante: str = "V0") -> str:
    """V0 = lo que hace hoy la app: orientar, separar papeles, OCR de cada uno (PDF: texto digital o página como imagen).
    T9: `variante` (V1–V4) transforma cada papel antes del OCR; el texto digital de un PDF no cambia."""
    from PIL import Image
    from ocr_module import digitize, orientacion, pdf as pdflib
    from parser_module.contable import MARCA
    data = ruta.read_bytes()
    if ruta.suffix.lower() == ".pdf":
        texto, data = pdflib.pagina(data, pagina)
        if texto is not None: return texto
    png, _ = orientacion.preparar_pagina(data, "auto")
    out = []
    from parser_module.contable.validar import numeros_de_nombre
    esperados = numeros_de_nombre(ruta.stem) if ruta.parent.name in ("comandas", "comanda") else None   # T8b, como app._leer_hoja
    for t in orientacion.separar(Image.open(io.BytesIO(png)).convert("RGB"), esperados=len(esperados) if esperados else None):
        if variante != "V0":
            from ocr_module.preprocess import variante as transformar
            t = transformar(t, variante)
            if t is None: raise RuntimeError(f"{variante} no disponible")
        b = io.BytesIO(); t.save(b, "PNG")
        r = digitize(b.getvalue(), motor)
        if not r.ok: raise RuntimeError(r.error)
        out.append(r.text)
    return f"\n{MARCA}\n".join(out)


def motor_relectura(eng):
    """Como app._motor: recorte (PIL) → texto con el mismo OCR (digitize). Un error sube."""
    from ocr_module import digitize
    def leer(img):
        b = io.BytesIO(); img.save(b, "PNG"); res = digitize(b.getvalue(), eng)
        if not res.ok: raise RuntimeError(res.error)
        return res.text
    leer.nombre = getattr(eng, "model", None) or getattr(eng, "name", "local"); return leer


def catalogo_del_libro(libro: Path) -> dict:
    """R6 solo LEYENDO: datos/catalogo.json y, si está vacío, los precios de los recibos buenos del libro (sin escribir nada)."""
    from parser_module.contable import catalogo
    precios = catalogo.cargar()
    if precios or not libro.exists(): return precios
    lib = json.loads(libro.read_text(encoding="utf-8"))
    return catalogo.construir([d for v in lib.values() if isinstance(v, dict) for d in v.get("documentos", [])])


def lector_completo(catalogo=None, leer_digitos=None, separar=None, preparar=None, hoja=None):
    """T16 · --completo: lee cada foto como la app (orientar → separar con esperados → relectura.leer_hoja con R3 y R6, sin carpeta
    de recortes). Devuelve (leer_hoja, leer_texto) para `ejecutar`: lo primero guarda los documentos y lo segundo los entrega;
    un recibo «dudoso» se mide como dudoso (sus motivos pasan a `avisos`). Inyectables para probar sin fotos ni OCR."""
    from PIL import Image
    from ocr_module import orientacion, pdf as pdflib
    from parser_module.contable import relectura, leer_texto as parsear_texto
    from parser_module.contable.validar import numeros_de_nombre
    separar = separar or orientacion.separar; preparar = preparar or orientacion.preparar_pagina; hoja = hoja or relectura.leer_hoja
    ultimo = {}

    def leer(ruta: Path, pagina, motor):
        data = ruta.read_bytes()
        if ruta.suffix.lower() == ".pdf":
            texto, data = pdflib.pagina(data, pagina)
            if texto is not None: ultimo["docs"] = parsear_texto(texto, "comandas"); return "completo"
        png, _ = preparar(data, "auto")
        en_comandas = ruta.parent.name in ("comandas", "comanda")
        nombre = ruta.name if en_comandas else ""
        esperados = numeros_de_nombre(nombre) if nombre else None
        trozos = separar(Image.open(io.BytesIO(png)).convert("RGB"), esperados=len(esperados) if esperados else None)
        h = hoja(trozos, motor, "comandas" if en_comandas else "", nombre,
                 separar=separar, catalogo=catalogo, leer_digitos=leer_digitos)
        docs = h["documentos"]
        for d in docs:
            if d.get("estado") == "dudoso": d["avisos"] = list(d.get("avisos") or []) + (d.get("motivos") or ["dudoso"])
        ultimo["docs"] = docs; return "completo"

    return leer, lambda texto, categoria: ultimo.get("docs", [])


def mas_dudosas(libro: dict, ref: dict, n: int) -> set:
    """T9 · Las n fotos (foto, página) de la referencia con más recibos «dudoso» en el libro (empate: más recibos en la referencia)."""
    from collections import Counter
    from parser_module.contable.asientos import estado_de
    from parser_module.contable.referencia import _foto_de
    mes = ref.get("mes", "")
    dud = Counter(_foto_de(d.get("origen", "")) for dia in libro.values() if isinstance(dia, dict) for d in dia.get("documentos", [])
                  if d.get("tipo") == "venta" and str(d.get("fecha", "")).startswith(mes) and estado_de(d) == "dudoso")
    en_ref = Counter((r["foto"], r["pagina"]) for r in ref["documentos"])
    return set(sorted(en_ref, key=lambda f: (-dud[f], -en_ref[f], f))[:n])


def ejecutar(mes, fotos, motor, leer_hoja, datos=DATOS, refrescar=False, variante="V0", muestra=None, semilla=7, peores=None, leer_texto=None) -> dict:
    if leer_texto is None:
        from parser_module.contable import leer_texto
    from parser_module.contable.referencia import congelar, huella, medir
    libro = datos / "libro.json"; refp = datos / "referencia" / f"referencia_{mes}.json"
    antes = huella(libro)
    if refrescar or not refp.exists(): congelar(libro, mes, refp)   # solo LEE el libro
    ref = json.loads(refp.read_text(encoding="utf-8"))
    if peores:                      # T9: las fotos que más dudosos dieron
        elegidas = mas_dudosas(json.loads(libro.read_text(encoding="utf-8")), ref, peores)
        ref = {**ref, "documentos": [r for r in ref["documentos"] if (r["foto"], r["pagina"]) in elegidas]}
    elif muestra:                   # T9: las mismas N fotos (semilla fija) para comparar variantes sin leer todo el mes
        import random
        fotos_ref = sorted({(r["foto"], r["pagina"]) for r in ref["documentos"]})
        elegidas = set(random.Random(semilla).sample(fotos_ref, min(muestra, len(fotos_ref))))
        ref = {**ref, "documentos": [r for r in ref["documentos"] if (r["foto"], r["pagina"]) in elegidas]}
    inf = medir(ref, fotos, lambda r, p: leer_hoja(r, p, motor), leer_texto)
    inf["variante"] = variante
    if peores: inf["peores"] = peores
    elif muestra: inf["muestra"], inf["semilla"] = muestra, semilla
    inf["huella_libro_antes"], inf["huella_libro_despues"] = antes, huella(libro)
    salida = datos / "referencia" / "informes" / f"{datetime.now():%Y%m%d-%H%M%S}{'' if variante == 'V0' else '_' + variante}.json"
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(json.dumps(inf, ensure_ascii=False, indent=1), encoding="utf-8")
    inf["archivo"] = str(salida)
    return inf


def comparar(informes: list) -> dict:
    """T9 · Una fila por variante: omitidos, dudosos, validados con error y acierto por campo."""
    return {"variantes": [{"variante": i["variante"], "omitidos": i["omitidos"], "dudosos": i["dudosos"],
                           "validados_con_error": i["validados_con_error"], "errores_lectura": len(i["errores_lectura"]),
                           "acierto": {c: v["acierto"] for c, v in i["por_campo"].items()}, "informe": i.get("archivo")} for i in informes]}


def mantenimiento(a, datos=DATOS):
    """T15 · R10, N5: exportar pares imagen/JSON y limpiar recortes. Solo LEE el libro."""
    from datetime import date
    from parser_module.contable import recortes, referencia
    carpeta = datos / "recortes"
    if a.exportar:
        ref = json.loads((datos / "referencia" / f"referencia_{a.mes}.json").read_text(encoding="utf-8"))
        r = referencia.exportar_entrenamiento(ref, carpeta, a.exportar)
        print(f"exportados {r['exportados']} · sin recorte {len(r['sin_recorte'])}")
    if a.borrar_recortes:
        print("borrados por fecha:", recortes.borrar(date.fromisoformat(a.borrar_recortes[0]), date.fromisoformat(a.borrar_recortes[1]), carpeta))
    if a.borrar_huerfanos:
        libro = json.loads((datos / "libro.json").read_text(encoding="utf-8"))
        usados = {d.get("recorte") for dia in libro.values() for d in dia.get("documentos", []) if d.get("recorte")}
        print("huérfanos borrados:", recortes.borrar_huerfanos(usados, carpeta))


def main():
    from functools import partial
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mes", required=True); ap.add_argument("--fotos", required=True, help="carpeta donde están las fotos (las rutas del libro son relativas a ella)")
    ap.add_argument("--motor", default="local"); ap.add_argument("--refrescar", action="store_true", help="volver a congelar la referencia desde el libro")
    ap.add_argument("--variantes", default="V0", help="lista separada por comas, p. ej. V0,V1,V2,V3,V4")
    ap.add_argument("--muestra", type=int, help="solo N fotos al azar (las mismas para todas las variantes)")
    ap.add_argument("--semilla", type=int, default=7)
    ap.add_argument("--peores", type=int, help="solo las N fotos con más recibos «dudoso» en el libro")
    ap.add_argument("--completo", action="store_true", help="T16: lee como la app (orientar, separar, relectura con R3/R6); informe «completo»")
    ap.add_argument("--exportar", metavar="CARPETA", help="T15: exporta imagen + JSON por recibo de la referencia del mes (no mide)")
    ap.add_argument("--borrar-recortes", nargs=2, metavar=("DESDE", "HASTA"), help="T15: borra recortes guardados entre dos fechas aaaa-mm-dd")
    ap.add_argument("--borrar-huerfanos", action="store_true", help="T15: borra recortes que ningún recibo del libro usa")
    a = ap.parse_args()
    if a.exportar or a.borrar_recortes or a.borrar_huerfanos: return mantenimiento(a)
    from ocr_module import get_engine
    from ocr_module.preprocess import _realesrgan_exe
    if a.completo:
        from ocr_module.digitos import numeros_tesseract
        motor = motor_relectura(get_engine(a.motor)); leer, parsear = lector_completo(catalogo_del_libro(DATOS / "libro.json"), numeros_tesseract)
        inf = ejecutar(a.mes, Path(a.fotos), motor, leer, refrescar=a.refrescar, variante="completo", muestra=a.muestra, semilla=a.semilla,
                       peores=a.peores, leer_texto=parsear)
        print(f"completo {inf['mes']}: {inf['total']} recibos · omitidos {inf['omitidos']} · dudosos {inf['dudosos']} · validados con error {inf['validados_con_error']}")
        for c, x in inf["por_campo"].items(): print(f"  {c:10s} {x['ok']:4d} ok {x['mal']:4d} mal  {'' if x['acierto'] is None else format(x['acierto'], '.1%')}")
        print("informe:", inf["archivo"]); return
    vs = [v.strip().upper() for v in a.variantes.split(",") if v.strip()]
    if any(v not in ("V0", "V1", "V2", "V3", "V4") for v in vs): ap.error(f"variantes válidas: V0–V4 (llegó {a.variantes})")
    if "V4" in vs and not _realesrgan_exe(): print("V4: no está realesrgan-ncnn-vulkan → se salta"); vs.remove("V4")
    motor, informes = get_engine(a.motor), []
    for i, v in enumerate(vs):
        inf = ejecutar(a.mes, Path(a.fotos), motor, partial(leer_hoja_v0, variante=v), refrescar=a.refrescar and not i, variante=v,
                      muestra=a.muestra, semilla=a.semilla, peores=a.peores)
        informes.append(inf)
        print(f"{v} {inf['mes']}: {inf['total']} recibos · omitidos {inf['omitidos']} · dudosos {inf['dudosos']} · validados con error {inf['validados_con_error']}")
        for c, x in inf["por_campo"].items(): print(f"  {c:10s} {x['ok']:4d} ok {x['mal']:4d} mal  {'' if x['acierto'] is None else format(x['acierto'], '.1%')}")
        print("informe:", inf["archivo"])
    if len(informes) > 1:
        salida = DATOS / "referencia" / "informes" / f"{datetime.now():%Y%m%d-%H%M%S}_variantes.json"
        salida.write_text(json.dumps(comparar(informes), ensure_ascii=False, indent=1), encoding="utf-8")
        print("comparación:", salida)


if __name__ == "__main__":
    sys.exit(main())
