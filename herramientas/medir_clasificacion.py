"""Mide el motor (N1): entrena con jun–ago (modelo temporal, no pisa el de producción) y prueba con los gastos de sept–oct del Excel manual.
Informe en logs/medir_clasificacion_AAAA-MM-DD.txt: acierto por ítem (crudo y con alias manual→PUC), por cuenta y lista de fallos con motivo.
Uso: python herramientas/medir_clasificacion.py [--manual ruta.xlsx] [--entrena jun,jul,ago] [--prueba 2026-09,2026-10]
Gate del plan: < 85 % por ítem o una cuenta con ≥ 10 ítems < 60 % → plan B (ADR)."""
from __future__ import annotations
import argparse, datetime as dt, json, re, sys
from collections import defaultdict
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP)); sys.path.insert(0, str(APP / "herramientas"))
import minar_manual as mm
from parser_module.contable.clasificar import Motor
from parser_module.contable.puc import puc_valida
from parser_module.numeros import norm

GATE_ITEM, GATE_CUENTA, MIN_ITEMS = 0.85, 0.60, 10


def pruebas(filas, meses):
    """filas de gasto del manual (débito, cuenta de gasto) en los meses de prueba, como en minar()."""
    return [x for x in filas if x["mes"] in meses and x["deb"] > 0 and not x["codigo"].startswith(mm.NO_GASTO)
            and "recaud" not in norm(x["desc"]) and "recuad" not in norm(x["desc"])]


PALANCAS = ("bigramas", "terceros", "frases", "choque", "cruce", "umbral")
UMBRAL_BASE = {"vecino": 0.75, "empate": 0.05}          # los de T5 (ADR-020)
BARRIDO_VECINO = (0.60, 0.65, 0.70, 0.75, 0.80); BARRIDO_EMPATE = (0.03, 0.04, 0.05, 0.06, 0.07, 0.08)
PRECISION_MIN = 0.90
LIBRO = APP / "datos" / "libro.json"


def indice_recibos(ruta: Path = LIBRO) -> dict:
    """(mes, consecutivo) → (detalle, valor) de los gastos de caja del libro: el texto OCR del papel que el motor verá en la app."""
    if not Path(ruta).is_file(): return {}
    idx = {}
    for dia in json.loads(Path(ruta).read_text(encoding="utf8")).values():
        for d in dia.get("documentos", []):
            if d.get("tipo") == "gasto_caja" and str(d.get("numero", "")).isdigit() and d.get("detalle"):
                idx[(str(d.get("fecha", ""))[:7], int(d["numero"]))] = (d["detalle"], float(d.get("valor") or 0))
    return idx


def numeros_recibo(desc: str) -> list[int]:
    """«Recibos 164, 165 y 166» → [164, 165, 166]; vacío si la descripción no cita recibos."""
    if not re.search(r"recibo", norm(desc)): return []
    return [int(n) for n in re.findall(r"(?<![\d.,])\d{2,4}(?![\d.,])", desc)]


def clasificar_fila(motor, x, recibos, cruce=True):
    r = motor.clasificar_item("gasto", x["desc"], x["tercero"])
    if not cruce or r["capa"] != "puente": return r
    nums = numeros_recibo(x["desc"])
    hallados = [recibos[(x["mes"], n)] for n in nums if (x["mes"], n) in recibos]
    if not hallados: return r
    voto = defaultdict(float); rs = {}
    for det, val in hallados:
        ri = motor.clasificar_item("gasto", det, x["tercero"])
        if ri["capa"] != "puente": voto[ri["cuenta"]] += val or 1; rs[ri["cuenta"]] = ri
    if not voto: return dict(r, motivo=f"{r['motivo']} · recibos {nums}: el texto del papel tampoco decide")
    c = max(voto, key=voto.get)
    return dict(rs[c], motivo=f"recibos {nums} (papel) · {rs[c]['motivo']}")


def motor_para(modelo, filas, entrena, cfg):
    """Motor con solo las palancas encendidas en cfg (conjunto de PALANCAS)."""
    from parser_module.contable import clasificar as cl
    modelo = dict(modelo)
    if "bigramas" not in cfg: modelo["bigramas"] = {}
    motor = Motor.desde_archivos()
    terc = mm.terceros(filas, entrena) if "terceros" in cfg else {}      # solo de los meses de entrenamiento (sin fuga)
    confirmar = dict(motor.confirmar)
    if "choque" not in cfg: confirmar["decisiones"] = []
    motor.__init__(modelo, confirmar, motor.aprendido, terc)
    return motor


def medir(filas, entrena, prueba, cfg=PALANCAS, umbral=None, recibos=None):
    """cfg: palancas encendidas; umbral: {vecino, empate} (por defecto los de T5 si 'umbral' no está en cfg)."""
    from parser_module.contable import clasificar as cl
    modelo = mm.minar(filas, entrena)
    motor = motor_para(modelo, filas, entrena, cfg)
    motor.umbral = motor.umbral | (umbral or ({} if "umbral" in cfg else UMBRAL_BASE))      # sin la palanca: los de T5
    frases = dict(cl.FRASES)
    if "frases" not in cfg: cl.FRASES.clear()
    try:
        recibos = indice_recibos() if recibos is None else recibos
        res = []
        for x in pruebas(filas, prueba):
            r = clasificar_fila(motor, x, recibos, "cruce" in cfg)
            esperada = puc_valida(x["codigo"], motor.alias, motor.notas)[0]
            res.append(dict(x=x, r=r, esperada=esperada, crudo=r["cuenta"] == x["codigo"], alias=r["cuenta"] == esperada))
    finally:
        cl.FRASES.clear(); cl.FRASES.update(frases)
    return modelo, res


def resumen(res):
    n = len(res); dec = [r for r in res if r["r"]["capa"] != "puente"]
    ok = sum(r["alias"] for r in res); okd = sum(r["alias"] for r in dec)
    return dict(n=n, ok=ok, item=ok / n if n else 0, dec=len(dec), cobertura=len(dec) / n if n else 0, precision=okd / len(dec) if dec else 0)


def barrer(filas, entrena, prueba, recibos):
    """umbral vecino × empate sobre la prueba; elige el más bajo (vecino, luego empate) con precisión de lo decidido ≥ 90 %."""
    tabla = []
    for v in BARRIDO_VECINO:
        for e in BARRIDO_EMPATE:
            tabla.append(((v, e), resumen(medir(filas, entrena, prueba, PALANCAS, dict(vecino=v, empate=e), recibos)[1])))
    ok = [t for t in tabla if t[1]["precision"] >= PRECISION_MIN]
    elegido = ok[0] if ok else max(tabla, key=lambda t: (t[1]["precision"], -t[0][0]))
    return tabla, elegido, bool(ok)


def informe(modelo, res, entrena, prueba):
    n = len(res); L = []
    pct = lambda a, b: f"{100 * a / b:.1f} %" if b else "—"
    ok_c, ok_a = sum(r["crudo"] for r in res), sum(r["alias"] for r in res)
    dec = [r for r in res if r["r"]["capa"] != "puente"]
    L += [f"Medición N1 · entrena {sorted(entrena)} ({len(modelo['lexico'])} palabras · {len(modelo['proveedores'])} proveedores · {len(modelo['vecinos'])} vecinos) · prueba {sorted(prueba)}",
          f"Ítems de prueba: {n}", f"Acierto crudo (código del manual tal cual): {ok_c}/{n} = {pct(ok_c, n)}",
          f"Acierto con alias (manual→PUC): {ok_a}/{n} = {pct(ok_a, n)}",
          f"Decididos sin puente: {len(dec)}/{n} = {pct(len(dec), n)} · acierto sobre los decididos (alias): {pct(sum(r['alias'] for r in dec), len(dec))}", ""]
    capas = defaultdict(lambda: [0, 0])
    for r in res: capas[r["r"]["capa"]][0] += 1; capas[r["r"]["capa"]][1] += r["alias"]
    L.append("Por capa (alias): " + " · ".join(f"{k} {v[1]}/{v[0]}" for k, v in sorted(capas.items())))
    cu = defaultdict(lambda: [0, 0, 0])
    for r in res: c = cu[r["esperada"]]; c[0] += 1; c[1] += r["alias"]; c[2] += r["crudo"]
    L += ["", "Por cuenta esperada (alias): cuenta · ítems · aciertos alias · %  (crudo)"]
    malas = []
    for k, (t, a, c) in sorted(cu.items(), key=lambda kv: -kv[1][0]):
        L.append(f"  {k}  {t:4d}  {a:4d}  {pct(a, t):>7}  (crudo {pct(c, t)})")
        if t >= MIN_ITEMS and a / t < GATE_CUENTA: malas.append(k)
    gate = ok_a / n >= GATE_ITEM and not malas if n else False
    L += ["", f"GATE (≥ 85 % por ítem y ninguna cuenta con ≥ {MIN_ITEMS} ítems < 60 %): {'PASA' if gate else 'FALLA'}"
          f" · alias {pct(ok_a, n)} · crudo {pct(ok_c, n)} · cuentas bajo 60 %: {', '.join(malas) or 'ninguna'}", "", "Fallos (alias):"]
    for r in res:
        if not r["alias"]:
            x = r["x"]; L.append(f"  {x['hoja'].split()[1].lower()} fila {x['fila']} · esperada {r['esperada']} (manual {x['codigo']}) · motor {r['r']['cuenta']} [{r['r']['capa']}] · "
                                 f"«{x['desc'][:50]}» / {x['tercero'][:30]} · {r['r']['motivo'][:90]}")
    return "\n".join(L), gate


def pct1(x): return f"{100 * x:.1f} %"


def extra(filas, entrena, prueba, recibos, elegido, tabla, hay):
    """barrido de umbrales, walk-forward y aporte de cada palanca → líneas del informe."""
    L = ["", "== Barrido de umbrales (prueba N1; vecino × empate → cobertura · precisión sobre decididos · acierto por ítem) =="]
    for (v, e), r in tabla: L.append(f"  vecino {v:.2f} empate {e:.2f} · {pct1(r['cobertura'])} · {pct1(r['precision'])} · {pct1(r['item'])}" + ("  ← elegido" if (v, e) == elegido[0] else ""))
    L.append(f"Elegido: vecino {elegido[0][0]:.2f} · empate {elegido[0][1]:.2f} " + ("(el más bajo con precisión ≥ 90 %)" if hay else "(NINGUNO llega a 90 %: se toma el de mayor precisión)"))
    um = dict(vecino=elegido[0][0], empate=elegido[0][1])
    L += ["", "== Walk-forward (umbral elegido) =="]
    for ent, pru in (({"jun", "jul", "ago"}, {"2026-09"}), ({"jun", "jul", "ago", "sep"}, {"2026-10"})):
        r = resumen(medir(filas, ent, pru, PALANCAS, um, recibos)[1])
        L.append(f"  {'+'.join(sorted(ent))} → {sorted(pru)[0]}: {r['ok']}/{r['n']} = {pct1(r['item'])} por ítem · cobertura {pct1(r['cobertura'])} · precisión decididos {pct1(r['precision'])}")
    L += ["", "== Aporte de cada palanca (N1 jun–ago → sept–oct; por ítem) =="]
    base = resumen(medir(filas, entrena, prueba, (), None, recibos)[1])
    full = resumen(medir(filas, entrena, prueba, PALANCAS, um, recibos)[1])
    L.append(f"  sin ninguna (como T5): {pct1(base['item'])} · todas: {pct1(full['item'])}")
    L.append("  palanca        sola (sobre T5)   quitada (de todas)")
    for p in PALANCAS:
        sola = resumen(medir(filas, entrena, prueba, (p,), um, recibos)[1]); sin = resumen(medir(filas, entrena, prueba, tuple(q for q in PALANCAS if q != p), um, recibos)[1])
        L.append(f"  {p:<13} {100 * (sola['item'] - base['item']):+6.1f} pp          {100 * (sin['item'] - full['item']):+6.1f} pp")
    L.append("  (Sept: el libro trae el texto del papel; octubre no está en el libro, así que el cruce solo actúa en sept.)")
    return L


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--manual", type=Path, default=mm.MANUAL)
    ap.add_argument("--entrena", default="jun,jul,ago"); ap.add_argument("--prueba", default="2026-09,2026-10")
    a = ap.parse_args(argv)
    entrena = {m.strip().lower()[:3] for m in a.entrena.split(",")}; prueba = {m.strip() for m in a.prueba.split(",")}
    filas = mm.leer_filas(a.manual); recibos = indice_recibos()
    tabla, elegido, hay = barrer(filas, entrena, prueba, recibos)
    modelo, res = medir(filas, entrena, prueba, PALANCAS, dict(vecino=elegido[0][0], empate=elegido[0][1]), recibos)
    txt, gate = informe(modelo, res, entrena, prueba)
    ext = extra(filas, entrena, prueba, recibos, elegido, tabla, hay)
    txt += "\n" + "\n".join(ext)
    destino = APP / "logs" / f"medir_clasificacion_{dt.date.today().isoformat()}.txt"
    destino.parent.mkdir(exist_ok=True); destino.write_text(txt, encoding="utf8")
    print("\n".join(txt.split("\n")[:12])); print("\n".join(ext[-25:])); print(f"\nInforme: {destino}")
    return 0 if gate else 1


if __name__ == "__main__": sys.exit(main())
