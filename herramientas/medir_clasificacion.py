"""Mide el motor (N1): entrena con jun–ago (modelo temporal, no pisa el de producción) y prueba con los gastos de sept–oct del Excel manual.
Informe en logs/medir_clasificacion_AAAA-MM-DD.txt: acierto por ítem (crudo y con alias manual→PUC), por cuenta y lista de fallos con motivo.
Uso: python herramientas/medir_clasificacion.py [--manual ruta.xlsx] [--entrena jun,jul,ago] [--prueba 2026-09,2026-10]
Gate del plan: < 85 % por ítem o una cuenta con ≥ 10 ítems < 60 % → plan B (ADR)."""
from __future__ import annotations
import argparse, datetime as dt, json, sys
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


def medir(filas, entrena, prueba):
    modelo = mm.minar(filas, entrena)
    motor = Motor.desde_archivos()
    motor.__init__(modelo, motor.confirmar, motor.aprendido)    # modelo temporal; confirmar y aprendido iguales
    res = []
    for x in pruebas(filas, prueba):
        r = motor.clasificar_item("gasto", x["desc"], x["tercero"])
        esperada = puc_valida(x["codigo"], motor.alias, motor.notas)[0]
        res.append(dict(x=x, r=r, esperada=esperada, crudo=r["cuenta"] == x["codigo"], alias=r["cuenta"] == esperada))
    return modelo, res


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


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--manual", type=Path, default=mm.MANUAL)
    ap.add_argument("--entrena", default="jun,jul,ago"); ap.add_argument("--prueba", default="2026-09,2026-10")
    a = ap.parse_args(argv)
    entrena = {m.strip().lower()[:3] for m in a.entrena.split(",")}; prueba = {m.strip() for m in a.prueba.split(",")}
    modelo, res = medir(mm.leer_filas(a.manual), entrena, prueba)
    txt, gate = informe(modelo, res, entrena, prueba)
    destino = APP / "logs" / f"medir_clasificacion_{dt.date.today().isoformat()}.txt"
    destino.parent.mkdir(exist_ok=True); destino.write_text(txt, encoding="utf8")
    print("\n".join(txt.split("\n")[:40])); print(f"\nInforme: {destino}")
    return 0 if gate else 1


if __name__ == "__main__": sys.exit(main())
