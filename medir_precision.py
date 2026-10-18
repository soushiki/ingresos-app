"""R9 / ADR-007: precisión del lector contra la referencia congelada. NUNCA escribe libro.json; solo la referencia y el informe.
    python medir_precision.py --mes 2026-09 --fotos "D:/ruta/a/las/fotos" [--motor local] [--refrescar]"""
import argparse, io, json, sys
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATOS = BASE / "datos"


def leer_hoja_v0(ruta: Path, pagina: int, motor) -> str:
    """V0 = lo que hace hoy la app: orientar, separar papeles, OCR de cada uno (PDF: texto digital o página como imagen)."""
    from PIL import Image
    from ocr_module import digitize, orientacion, pdf as pdflib
    from parser_module.contable import MARCA
    data = ruta.read_bytes()
    if ruta.suffix.lower() == ".pdf":
        texto, data = pdflib.pagina(data, pagina)
        if texto is not None: return texto
    png, _ = orientacion.preparar_pagina(data, "auto")
    out = []
    for t in orientacion.separar(Image.open(io.BytesIO(png)).convert("RGB")):
        b = io.BytesIO(); t.save(b, "PNG")
        r = digitize(b.getvalue(), motor)
        if not r.ok: raise RuntimeError(r.error)
        out.append(r.text)
    return f"\n{MARCA}\n".join(out)


def ejecutar(mes, fotos, motor, leer_hoja, datos=DATOS, refrescar=False) -> dict:
    from parser_module.contable import leer_texto
    from parser_module.contable.referencia import congelar, huella, medir
    libro = datos / "libro.json"; refp = datos / "referencia" / f"referencia_{mes}.json"
    antes = huella(libro)
    if refrescar or not refp.exists(): congelar(libro, mes, refp)   # solo LEE el libro
    ref = json.loads(refp.read_text(encoding="utf-8"))
    inf = medir(ref, fotos, lambda r, p: leer_hoja(r, p, motor), leer_texto)
    inf["huella_libro_antes"], inf["huella_libro_despues"] = antes, huella(libro)
    salida = datos / "referencia" / "informes" / f"{datetime.now():%Y%m%d-%H%M%S}.json"
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(json.dumps(inf, ensure_ascii=False, indent=1), encoding="utf-8")
    inf["archivo"] = str(salida)
    return inf


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mes", required=True); ap.add_argument("--fotos", required=True, help="carpeta donde están las fotos (las rutas del libro son relativas a ella)")
    ap.add_argument("--motor", default="local"); ap.add_argument("--refrescar", action="store_true", help="volver a congelar la referencia desde el libro")
    a = ap.parse_args()
    from ocr_module import get_engine
    inf = ejecutar(a.mes, Path(a.fotos), get_engine(a.motor), leer_hoja_v0, refrescar=a.refrescar)
    print(f"{inf['mes']}: {inf['total']} recibos · omitidos {inf['omitidos']} · dudosos {inf['dudosos']} · validados con error {inf['validados_con_error']}")
    for c, v in inf["por_campo"].items(): print(f"  {c:10s} {v['ok']:4d} ok {v['mal']:4d} mal  {'' if v['acierto'] is None else format(v['acierto'], '.1%')}")
    print("informe:", inf["archivo"])


if __name__ == "__main__":
    sys.exit(main())
