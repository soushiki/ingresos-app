"""Spike ADR-024 / T5d (fuera de la app): ¿la capa «ml» (TF-IDF char_wb 2–5 + regresión logística, sklearn) lleva el N1 a ≥ 85 %?
Entrena SOLO con jun–ago y mide sept–oct reutilizando medir_clasificacion.medir (motor + palancas + cruce «Recibo N»);
la capa ml actúa solo donde el motor deja la puente (entre vecino y puente) y p ≥ umbral y p1−p2 ≥ margen; `puc_valida` va al final.
Necesita requirements-entrenar.txt. Informe en logs/spike_ml_AAAA-MM-DD.txt. No toca el motor ni el modelo de producción.
Uso: python herramientas/spike_ml.py [--manual ruta.xlsx]"""
from __future__ import annotations
import argparse, datetime as dt, sys
from collections import defaultdict
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP)); sys.path.insert(0, str(APP / "herramientas"))
import minar_manual as mm
import medir_clasificacion as mc
from parser_module.contable.clasificar import Motor
from parser_module.contable.puc import puc_valida
from parser_module.numeros import norm

UMBRALES = [round(0.30 + 0.05 * i, 2) for i in range(11)]       # 0,30–0,80
MARGENES = [0.0, 0.05, 0.10, 0.15, 0.20]
CS = (1.0, 10.0, 100.0)                                          # C de la regresión logística
PRECISION_MIN = 0.90


def texto(desc, tercero, papel=""):
    """lo que ve la capa: descripción + proveedor (+ texto OCR del papel cuando hay cruce «Recibo N»), normalizado."""
    return " ".join(norm(f"{desc} {tercero} {papel}").split())


def papel_de(x, recibos):
    return " ".join(recibos[(x["mes"], n)][0] for n in mc.numeros_recibo(x["desc"]) if (x["mes"], n) in recibos)


def entrenar(filas, entrena, motor, recibos, C):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    X, y = [], []
    for x in filas:
        if norm(x["hoja"].split()[1])[:3] not in entrena or x["mes"] > "2026-08": continue
        if not (x["deb"] > 0 and not x["codigo"].startswith(mm.NO_GASTO) and "recaud" not in norm(x["desc"]) and "recuad" not in norm(x["desc"])): continue
        X.append(texto(x["desc"], x["tercero"], papel_de(x, recibos))); y.append(puc_valida(x["codigo"], motor.alias, motor.notas)[0])
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True)
    clf = LogisticRegression(C=C, max_iter=2000).fit(vec.fit_transform(X), y)
    return vec, clf, len(X)


def aplicar(res, probas, clases, motor, umbral, margen):
    """→ lista de (acierto, capa) con la capa ml sobre las filas que quedaron en la puente."""
    out = []
    for r, p in zip(res, probas):
        capa, ok = r["r"]["capa"], r["alias"]
        if capa == "puente":
            o = sorted(range(len(p)), key=lambda i: -p[i])
            p1, p2 = p[o[0]], (p[o[1]] if len(o) > 1 else 0.0)
            if p1 >= umbral and p1 - p2 >= margen:
                cuenta, estado, _ = puc_valida(clases[o[0]], motor.alias, motor.notas)
                if estado in ("ok", "propia"): capa, ok = "ml", cuenta == r["esperada"]
        out.append((ok, capa))
    return out


def resumen(par):
    n = len(par); dec = [a for a, c in par if c != "puente"]
    return dict(n=n, item=sum(a for a, _ in par) / n, cobertura=len(dec) / n, precision=sum(dec) / len(dec) if dec else 0, ml=sum(c == "ml" for _, c in par), ml_ok=sum(a for a, c in par if c == "ml"))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0]); ap.add_argument("--manual", type=Path, default=mm.MANUAL)
    a = ap.parse_args(argv)
    entrena, prueba = {"jun", "jul", "ago"}, {"2026-09", "2026-10"}
    filas = mm.leer_filas(a.manual); recibos = mc.indice_recibos()
    um = mc.UMBRAL_BASE
    modelo, res = mc.medir(filas, entrena, prueba, mc.PALANCAS, um, recibos)       # el motor de T5c, entrenado solo con jun–ago
    motor = mc.motor_para(modelo, filas, entrena, mc.PALANCAS); motor.umbral = motor.umbral | um
    base = resumen([(r["alias"], r["r"]["capa"]) for r in res])
    L = [f"Spike ml (T5d) · entrena jun–ago, prueba sept–oct · ítems {base['n']}",
         f"Sin capa ml (motor T5c): {100 * base['item']:.1f} % por ítem · cobertura {100 * base['cobertura']:.1f} % · precisión decididos {100 * base['precision']:.1f} %", ""]
    mejor = None
    for C in CS:
        vec, clf, ntr = entrenar(filas, entrena, motor, recibos, C)
        probas = clf.predict_proba(vec.transform([texto(r["x"]["desc"], r["x"]["tercero"], papel_de(r["x"], recibos)) for r in res]))
        L.append(f"== C = {C:g} · {ntr} ejemplos de entrenamiento · {len(clf.classes_)} cuentas ==")
        tabla = []
        for u in UMBRALES:
            for m in MARGENES:
                par = aplicar(res, probas, list(clf.classes_), motor, u, m); s = resumen(par); tabla.append(((u, m), s, par))
                L.append(f"  umbral {u:.2f} margen {m:.2f} · N1 {100 * s['item']:.1f} % · cobertura {100 * s['cobertura']:.1f} % · precisión {100 * s['precision']:.1f} % · ml decide {s['ml']} (acierta {s['ml_ok']})")
        ok = [t for t in tabla if t[1]["precision"] >= PRECISION_MIN]
        elegido = ok[0] if ok else max(tabla, key=lambda t: (t[1]["precision"], t[1]["item"]))
        L.append(f"  elegido C={C:g}: umbral {elegido[0][0]:.2f} margen {elegido[0][1]:.2f} " + ("(el más bajo con precisión ≥ 90 %)" if ok else "(NINGUNO llega a 90 %: mayor precisión)") + f" → N1 {100 * elegido[1]['item']:.1f} %")
        L.append("")
        if mejor is None or (bool(ok), elegido[1]["item"]) > (mejor[3], mejor[2]["item"]): mejor = (C, elegido[0], elegido[1], bool(ok), elegido[2])
    C, (u, m), s, hay, par = mejor
    cu = defaultdict(lambda: [0, 0, 0])
    for r, (acierto, _) in zip(res, par): c = cu[r["esperada"]]; c[0] += 1; c[1] += acierto; c[2] += r["alias"]
    malas = sorted(k for k, (t, ok_, _) in cu.items() if t >= mc.MIN_ITEMS and ok_ / t < mc.GATE_CUENTA)
    L += [f"== ELEGIDO: C={C:g} · umbral {u:.2f} · margen {m:.2f} ==",
          f"N1 por ítem: {100 * base['item']:.1f} % → {100 * s['item']:.1f} % (aporte de ml {100 * (s['item'] - base['item']):+.1f} pp) · cobertura {100 * s['cobertura']:.1f} % · precisión decididos {100 * s['precision']:.1f} %",
          f"ml decide {s['ml']} ítems, acierta {s['ml_ok']}",
          f"Cuentas con ≥ {mc.MIN_ITEMS} ítems bajo 60 %: {', '.join(malas) or 'ninguna'}",
          f"MINI-GATE N1 ≥ 85 %: {'PASA' if s['item'] >= mc.GATE_ITEM and not malas else 'FALLA'}"]
    destino = APP / "logs" / f"spike_ml_{dt.date.today().isoformat()}.txt"
    destino.parent.mkdir(exist_ok=True); destino.write_text("\n".join(L), encoding="utf8")
    print("\n".join(L[:3])); print("\n".join(l for l in L if l.startswith("  elegido") or l.startswith("==") or l.startswith("N1") or l.startswith("ml ") or l.startswith("Cuentas") or l.startswith("MINI"))); print(f"Informe: {destino}")
    return 0 if s["item"] >= mc.GATE_ITEM and not malas else 1


if __name__ == "__main__": sys.exit(main())
