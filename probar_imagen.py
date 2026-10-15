"""Prueba con UNA imagen: lee (módulo 1), interpreta con TUS columnas (módulo 2) y evalúa si el resultado sirve.

    python probar_imagen.py recibo.jpg
    python probar_imagen.py recibo.jpg --model qwen3-vl:8b
    python probar_imagen.py recibo.jpg --esquema datos/esquema.json
Crea prueba_out/prueba_<imagen>.html (foto y texto lado a lado) y .txt, y lo abre en el navegador."""
import argparse, base64, html, re, sys, webbrowser
from pathlib import Path
try:
    from dotenv import load_dotenv; load_dotenv()
except ImportError:
    pass
from ocr_module import digitize, get_engine
from ocr_module.preprocess import prepare
from parser_module import Config, Esquema, parsear

ICONO = {"ok": "✓", "revisar": "⚠", "faltante": "✗"}
CLS = {"ok": "ok", "revisar": "warn", "faltante": "bad"}


def veredicto(ok, total, fallan):
    p = ok / max(1, total)
    if p >= 0.8 and not fallan: return "MUY ÚTIL", "ok", "Casi todas las columnas salieron con valor y los controles cuadran."
    if p >= 0.5: return "ÚTIL CON REVISIÓN", "warn", "Hay datos aprovechables; revisa las celdas dudosas y los controles que no cuadran."
    return "POCO ÚTIL", "bad", "Se reconocen pocas columnas. Prueba otro modelo, una foto más nítida o ajusta los sinónimos de las columnas."


def informe(res, c, esq, vals, todo, fallan, v, img_b64, out):
    e = html.escape
    t = re.sub(r"(\[\?\]|\[ilegible\])", r"<mark>\1</mark>", e(res.text))
    fmt = lambda n: f"{round(n):,}".replace(",", ".")
    filas = ""
    for k in esq.claves:
        n = esq.nombres[k]
        if esq.tipos[k] == "calculo":
            filas += f"<tr><td>{e(n)} ƒ</td><td class='ok'>calculada</td><td></td><td class='n'>{fmt(todo[k])}</td></tr>"; continue
        f = c.campos[k]; val = "" if f.valor is None else fmt(f.valor)
        filas += f"<tr><td>{e(n)}</td><td class='{CLS[f.estado]}'>{ICONO[f.estado]} {f.estado}</td><td>{e('; '.join(f.razones) or f.linea)}</td><td class='n'>{val}</td></tr>"
    ctl = "".join(f"<li><b>{e(x['nombre'])}</b> — diferencia {fmt(x['diferencia'])}</li>" for x in fallan) or "<li class='m'>Todos los controles cuadran.</li>"
    ok, tot, lab, cls, msg = v
    out.write_text(f"""<!DOCTYPE html><html lang="es"><head><meta charset="utf-8"><title>Prueba</title><style>
body{{margin:0;font:15px/1.4 system-ui,sans-serif;background:#eaf4fd;color:#12324f}}header{{padding:14px 22px;background:linear-gradient(90deg,#4aa3ef,#7cc0f7);color:#fff}}h1{{margin:0;font-size:19px}}
.g{{display:grid;grid-template-columns:1fr 1fr;gap:16px;padding:16px 22px}}@media(max-width:900px){{.g{{grid-template-columns:1fr}}}}
.c{{background:#fff;border:1px solid #cfe3f6;border-radius:14px;padding:14px;overflow:auto;max-height:90vh}}.c h2{{margin:0 0 10px;font-size:14px;text-transform:uppercase;color:#17466f}}
img{{max-width:100%;border-radius:8px}}pre{{white-space:pre-wrap;margin:0;font:13px/1.5 ui-monospace,Consolas,monospace}}mark{{background:#ffe08a}}
table{{border-collapse:collapse;width:100%}}td,th{{padding:6px 8px;border-top:1px solid #dcebf8;text-align:left;font-size:13px}}th{{background:#d9ecfc;border:0}}
.ok{{color:#1f9d6b;font-weight:600}}.warn{{color:#b7791f;font-weight:600}}.bad{{color:#d6453d;font-weight:600}}.n{{font-weight:700;text-align:right}}.m{{color:#5b7a96}}
.v{{grid-column:1/-1}}.tag{{display:inline-block;padding:4px 12px;border-radius:99px;color:#fff;font-weight:700}}.tag.ok{{background:#1f9d6b;color:#fff}}.tag.warn{{background:#e0a030;color:#fff}}.tag.bad{{background:#d6453d;color:#fff}}
</style></head><body><header><h1>Prueba · {e(Path(res.source).name)}</h1></header><div class="g">
<div class="c v"><span class="tag {cls}">{lab}</span> &nbsp;{msg}<p class="m" style="margin:8px 0 0">Motor: {e(res.engine)} · modelo: {e(res.model)} · {res.seconds}s · columnas con valor: {ok}/{tot}. Verifica los dígitos contra la foto.</p></div>
<div class="c"><h2>Foto</h2><img src="data:image/jpeg;base64,{img_b64}"></div>
<div class="c"><h2>Texto digitalizado</h2><pre>{t}</pre></div>
<div class="c"><h2>Tus columnas</h2><table><tr><th>Columna</th><th>Estado</th><th>Línea leída / motivo</th><th>Valor</th></tr>{filas}</table></div>
<div class="c"><h2>Controles</h2><ul>{ctl}</ul></div></div></body></html>""", encoding="utf8")


def main():
    ap = argparse.ArgumentParser(description="Prueba el sistema con una sola imagen")
    ap.add_argument("imagen")
    ap.add_argument("--engine", default="local", choices=["local", "tesseract", "gemini"])
    ap.add_argument("--model", default=None)
    ap.add_argument("--esquema", default="datos/esquema.json", help="tus columnas; si no existe se usa la plantilla Restaurante · ganancias y pérdidas")
    ap.add_argument("--out", default="prueba_out")
    ap.add_argument("--no-open", action="store_true")
    a = ap.parse_args()
    p = Path(a.imagen)
    if not p.is_file(): sys.exit(f"No existe: {p}")
    esq = Esquema.cargar(a.esquema, Esquema.plantilla("restaurante_pyg"))
    try: eng = get_engine(a.engine, **({"model": a.model} if a.model and a.engine != "tesseract" else {}))
    except Exception as ex: sys.exit(f"No pude iniciar el motor: {ex}")
    print(f"Analizando {p.name} con {eng.name} ({eng.model})… (las fotos largas se leen por trozos)")
    res = digitize(p, eng)
    if not res.ok: sys.exit(f"\n✗ Falló: {res.error}")
    c = parsear(res.text, Config.cargar("datos/alias_negocio.json", esq), fuente=p.name)
    vals = {k: (c.campos[k].valor or 0) for k in esq.claves if esq.tipos[k] != "calculo"}
    todo, fallan = esq.evaluar(vals), esq.controlar(vals)
    ent = [k for k in esq.claves if esq.tipos[k] != "calculo"]
    ok = sum(c.campos[k].estado == "ok" for k in ent)
    v = (ok, len(ent)) + veredicto(ok, len(ent), fallan)
    print(f"\n{'─'*60}\n{res.text}\n{'─'*60}\n⏱  {res.seconds}s · fecha: {c.fecha or '—'} · columnas con valor: {ok}/{len(ent)}")
    for k in esq.claves:
        if esq.tipos[k] == "calculo": print(f"  ƒ {esq.nombres[k]:<32} {round(todo[k]):>12,}".replace(",", ".")); continue
        f = c.campos[k]
        print(f"  {ICONO[f.estado]} {esq.nombres[k]:<32} {'' if f.valor is None else f'{f.valor:,}'.replace(',', '.'):>12}  {'; '.join(f.razones)}")
    for x in fallan: print(f"  ! {x['nombre']} (diferencia {x['diferencia']:,.0f})".replace(",", "."))
    print(f"\nVeredicto: {v[2]} — {v[4]}")
    out = Path(a.out); out.mkdir(exist_ok=True)
    (out / f"prueba_{p.stem}.txt").write_text(res.text, encoding="utf8")
    data, _ = prepare(p, max_side=2000, min_side=800, enhance=False)
    rep = out / f"prueba_{p.stem}.html"
    informe(res, c, esq, vals, todo, fallan, v, base64.b64encode(data).decode(), rep)
    print(f"Informe: {rep.resolve()}")
    if not a.no_open: webbrowser.open(rep.resolve().as_uri())


if __name__ == "__main__":
    main()
