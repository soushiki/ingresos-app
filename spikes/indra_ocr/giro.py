"""Orientation test: the app's step (orientacion.preparar_pagina = Tesseract OSD, quarter turns only, no deskew) vs Indra's
upright() (orient.onnx quarter turns + deskew up to ±45°). Each of the 20 sheets, made upright as the app does, is rotated by
ANGULOS (counter-clockwise, white fill), oriented by each method, then the SAME rest: recortar → separar(esperados) → Indra
(filas) on each crop → numbers. Scores per sheet: true receipt numbers and true totals seen; quarter turn right; tilt left.
One line per case + checkpoint (resultados/avance_giro.json): re-run to resume."""
import io, json, sys, time
from pathlib import Path

AQUI = Path(__file__).resolve().parent; APP = AQUI.parent.parent; FOTOS = Path(r"D:\Claude\image_to_text\data\SEPTIEMBRE")
RES = AQUI / "resultados"; RES.mkdir(exist_ok=True)
sys.path[:0] = [str(APP), str(AQUI)]
from PIL import Image
from ocr_module import orientacion
from ocr_module.digitos import _enteros
from parser_module.contable.validar import numeros_de_nombre
from indra_cliente import Indra
from ocr_module.digitos import numeros_tesseract
LECTOR = sys.argv[1] if len(sys.argv) > 1 else "indra"   # reader of the crops: indra (deskews each crop itself) | tesseract (does not)

ANGULOS = [0, 90, 180, 270, 4, -8, 15, -25, 40, 100, 200, -80]
ref = json.loads((APP / "datos/referencia/referencia_2026-09.json").read_text(encoding="utf-8"))
sub = set(json.loads((APP / "datos/referencia/google/subconjunto.json").read_text(encoding="utf-8")))
fotos = sorted({r["foto"] for r in ref["documentos"] if r["numero"] in sub})
total = lambda d: (d.get("consumo") or 0) + (d.get("domicilio") or 0) + (d.get("propina") or 0)
por_foto = {f: [(int(r["numero"]), total(r["documento"])) for r in ref["documentos"] if r["foto"] == f] for f in fotos}

eng = Indra(threads=4, layout="filas")
def resto(img, foto):
    """Same for both methods: trim margins, split with the expected count, Indra reads each crop → set of integers + crops."""
    img = orientacion.recortar(img); esp = numeros_de_nombre(Path(foto).stem)
    trozos = orientacion.separar(img, esperados=len(esp) if esp else None)
    vistos = set()
    for t in trozos: vistos |= _enteros(eng.texto(t)) if LECTOR == "indra" else (numeros_tesseract(t) or set())
    return vistos, len(trozos)

def png(img):
    b = io.BytesIO(); img.save(b, "PNG"); return b.getvalue()

sufijo = "" if LECTOR == "indra" else "_" + LECTOR
av = RES / f"avance_giro{sufijo}.json"
hechas = json.loads(av.read_text(encoding="utf-8")) if av.exists() else {}
n, t0, nuevas = len(fotos) * len(ANGULOS), time.monotonic(), 0
for foto in fotos:
    base = None
    for ang in ANGULOS:
        clave = f"{foto}@{ang}"
        if clave in hechas: continue
        if base is None:                                   # upright as the app does it (Tesseract OSD on the original)
            orig = Image.open(FOTOS / foto).convert("RGB"); g0, c0 = orientacion.giro_automatico(orig)
            base = orig.rotate(-g0, expand=True) if g0 and c0 >= orientacion.CONFIANZA_MIN else orig
        rot = base.rotate(ang, expand=True, fillcolor="white", resample=Image.BICUBIC)
        q = round(ang / 90) % 4                            # quarter turns (ccw) the content was turned
        a = time.perf_counter(); pg, g = orientacion.preparar_pagina(png(rot), "auto"); ta = time.perf_counter() - a
        app_img = Image.open(io.BytesIO(pg)).convert("RGB")
        a = time.perf_counter(); ind_img, k, sk, _ = eng.upright(rot); ti = time.perf_counter() - a
        fila = {"q": q}
        for nombre, img, cuarto, ts in (("app", app_img, (g // 90) % 4 == q, ta), ("indra", ind_img, k == q, ti)):   # g: clockwise
            vistos, ntro = resto(img, foto)
            fila[nombre] = {"cuarto_ok": cuarto, "numeros": sum(nu in vistos for nu, _ in por_foto[foto]),
                            "totales": sum(to in vistos for _, to in por_foto[foto]), "recortes": ntro, "s": round(ts, 2)}
        fila["indra"]["k"], fila["indra"]["skew"] = k, sk
        fila["indra"]["inclinacion_restante"] = round(abs(ang - 90 * round(ang / 90) + sk), 1) if k == q else None
        fila["app"]["g"] = g
        hechas[clave] = fila; nuevas += 1
        tmp = av.with_suffix(".tmp"); tmp.write_text(json.dumps(hechas), encoding="utf-8")
        for intento in range(20):                          # Windows: antivirus/indexer can hold the file for a moment
            try: tmp.replace(av); break
            except PermissionError: time.sleep(0.5)
        m = (time.monotonic() - t0) / nuevas; de = len(por_foto[foto])
        print(f"[{len(hechas)}/{n}] {foto} @{ang:+d}°: app {fila['app']['numeros']}/{de} núm · indra {fila['indra']['numeros']}/{de} núm "
              f"(k={k}, skew={sk:+.1f}) · {m:.0f} s/caso · quedan ≈ {(n - len(hechas)) * m / 60:.0f} min", flush=True)
eng.cerrar()

res = {}
for ang in ANGULOS:
    filas = [hechas[f"{f}@{ang}"] for f in fotos]; R = sum(len(por_foto[f]) for f in fotos)
    res[str(ang)] = {m: {"cuarto_ok": sum(x[m]["cuarto_ok"] for x in filas), "numeros": sum(x[m]["numeros"] for x in filas),
                         "totales": sum(x[m]["totales"] for x in filas), "s_giro": round(sum(x[m]["s"] for x in filas) / len(filas), 2)}
                     for m in ("app", "indra")} | {"recibos": R, "hojas": len(filas),
                                                   "indra_inclinacion_restante_max": max((x["indra"]["inclinacion_restante"] for x in filas if x["indra"].get("inclinacion_restante") is not None), default=None),
                                                   "app_inclinacion_restante": abs(ang - 90 * round(ang / 90))}
(RES / f"resultado_giro{sufijo}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
av.unlink(missing_ok=True); print(json.dumps(res, ensure_ascii=False))
