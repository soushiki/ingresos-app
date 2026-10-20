"""R3 head-to-head: Tesseract-dígitos (ocr_module.digitos.numeros_tesseract, as the app runs it) vs Indra as the second reader.
Same 20 photos / 107 receipts as comparar.py. Each crop (orientacion.separar) is read by both; the crop is matched to its
reference receipt by the union of what both readers see (neither is favoured). Per receipt and reader:
  confirma  the true receipt number / true total (consumo+domicilio+propina) is in the reader's number set (no false note)
  atrapa    for each real qwen mistake on the total (reports 20261018-040428 V0 and 20261018-120343 completo), the wrong total
            is NOT in the set while the true one is (R3 leaves the note «Sin confirmar» on the wrong value)
One line per photo + checkpoint (resultados/avance_r3.json): re-run to resume."""
import io, json, sys, time
from pathlib import Path

AQUI = Path(__file__).resolve().parent; APP = AQUI.parent.parent; FOTOS = Path(r"D:\Claude\image_to_text\data\SEPTIEMBRE")
RES = AQUI / "resultados"; RES.mkdir(exist_ok=True)
sys.path[:0] = [str(APP), str(AQUI)]
from PIL import Image
from ocr_module import orientacion
from ocr_module.digitos import _enteros, numeros_tesseract
from parser_module.contable.validar import numeros_de_nombre
from indra_cliente import Indra

ref = json.loads((APP / "datos/referencia/referencia_2026-09.json").read_text(encoding="utf-8"))
sub = set(json.loads((APP / "datos/referencia/google/subconjunto.json").read_text(encoding="utf-8")))
fotos = sorted({(r["foto"], r["pagina"]) for r in ref["documentos"] if r["numero"] in sub})
docs = {r["numero"]: r["documento"] for r in ref["documentos"] if (r["foto"], r["pagina"]) in set(fotos)}
total = lambda d: (d.get("consumo") or 0) + (d.get("domicilio") or 0) + (d.get("propina") or 0)

# qwen's real mistakes on the total (V0 one pass + full loop), from the existing reports
errores = {}
for f in ("20261018-040428.json", "20261018-120343_completo.json"):
    for e in json.loads((APP / "datos/referencia/informes" / f).read_text(encoding="utf-8"))["detalle"]:
        c = e["campos"]
        if e["numero"] in docs and any(k in c for k in ("consumo", "domicilio", "propina")):
            d = docs[e["numero"]]; malo = total({**d, **{k: v["leido"] for k, v in c.items()}})
            if malo != total(d) and malo: errores.setdefault(e["numero"], set()).add(malo)

av = RES / "avance_r3.json"
hechas = json.loads(av.read_text(encoding="utf-8")) if av.exists() else {}
eng = Indra(threads=4, layout="filas"); t0 = time.monotonic(); nuevas = 0
for i, (foto, _) in enumerate(fotos, 1):
    if foto in hechas: continue
    ruta = FOTOS / foto
    png, _ = orientacion.preparar_pagina(ruta.read_bytes(), "auto")
    esp = numeros_de_nombre(ruta.stem)
    trozos = orientacion.separar(Image.open(io.BytesIO(png)).convert("RGB"), esperados=len(esp) if esp else None)
    out = []
    for t in trozos:
        a = time.perf_counter(); tes = numeros_tesseract(t); b = time.perf_counter(); ind = _enteros(eng.texto(t)); c = time.perf_counter()
        out.append({"tes": sorted(tes), "ind": sorted(ind), "tes_s": round(b - a, 3), "ind_s": round(c - b, 3)})
    hechas[foto] = out; nuevas += 1
    tmp = av.with_suffix(".tmp"); tmp.write_text(json.dumps(hechas), encoding="utf-8"); tmp.replace(av)
    m = (time.monotonic() - t0) / nuevas
    print(f"[{len(hechas)}/{len(fotos)}] {foto}: {len(out)} recortes · {m:.1f} s/foto · quedan ≈ {(len(fotos) - len(hechas)) * m / 60:.1f} min", flush=True)
mem_indra = eng.cerrar()["peak_rss_mb"]

# match each crop to its reference receipt by the union of both sets (number first, then total)
r = {k: {"num": 0, "tot": 0, "atrapa": 0, "confirma_malo": 0, "s": 0.0, "tam": 0, "dudoso_falso": 0} for k in ("tes", "ind")}
casados, sin_casar, n_err = set(), 0, 0
for foto, _ in fotos:
    nums = [x["numero"] for x in ref["documentos"] if x["foto"] == foto]
    for cr in hechas[foto]:
        u = set(cr["tes"]) | set(cr["ind"])
        cand = [n for n in nums if n not in casados and int(n) in u] or [n for n in nums if n not in casados and total(docs[n]) in u]
        for k in r: r[k]["s"] += cr[k + "_s"]; r[k]["tam"] += len(cr[k])
        if len(cand) != 1: sin_casar += 1; continue
        n = cand[0]; casados.add(n); d = docs[n]
        for k in r:
            s = set(cr[k]); r[k]["num"] += int(n) in s; r[k]["tot"] += total(d) in s
            r[k]["dudoso_falso"] += int(n) not in s and bool((set(numeros_de_nombre(Path(foto).stem) or ()) - {int(n)}) & s)   # R3b motive on a correct receipt
            for malo in errores.get(n, ()):
                r[k]["atrapa"] += total(d) in s and malo not in s; r[k]["confirma_malo"] += malo in s
        n_err += len(errores.get(n, ()))
recortes = sum(len(v) for v in hechas.values())
res = {"recibos": len(docs), "recortes": recortes, "casados": len(casados), "sin_casar": sin_casar, "errores_qwen_en_casados": n_err,
       "lectores": {k: {"confirma_numero": v["num"], "confirma_total": v["tot"], "atrapa_error_qwen": v["atrapa"],
                        "confirma_error_qwen": v["confirma_malo"], "dudoso_falso_r3b": v["dudoso_falso"], "s_por_recorte": round(v["s"] / recortes, 3),
                        "numeros_por_recorte": round(v["tam"] / recortes, 1)} for k, v in r.items()},
       "pico_ram_indra_mb": mem_indra}
(RES / "resultado_r3.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
av.unlink(missing_ok=True); print(json.dumps(res, ensure_ascii=False))
