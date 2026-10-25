"""Spike T1 (M-27, riesgo 2): de las facturas de septiembre del libro, ¿cuántas dan >= 1 ítem con valor y cuántas suman el total +-1 %?
Solo lee datos/libro.json; no escribe nada. Uso: python spikes/spike_items_factura.py [--mes 2026-09] [--ver 5]"""
import argparse, json, re, sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from parser_module.contable.documentos import monto, montos
from parser_module.numeros import norm

NO = re.compile(r"descripcion|total|\bcant\b|vr\.? ?unit|subtotal|iva|domicilio|propina|dcto|descuento|efectivo|cambio|nit|cufe|fecha|telefono")
NUM = r"\$?\s*\d[\d.,]*"
TOPE = 5_000_000   # un ítem mayor es un NIT, CUFE o resolución, no un valor


def items_tabla(texto):
    """Filas con '|': el valor es el último número de la fila (VR. TOTAL); la cantidad, el primero si va solo al inicio."""
    out = []
    for l in texto.splitlines():
        if l.count("|") < 2 or NO.search(norm(l)): continue
        celdas = [c.strip() for c in l.split("|") if c.strip()]
        nums = [c for c in celdas if re.fullmatch(NUM, c)]
        nom = next((c for c in celdas if re.search(r"[^\W\d_]{3,}", c)), "")
        if nom and nums:
            v = monto(nums[-1])
            if 0 < v < TOPE: out.append(dict(nombre=nom, valor=v))
    return out


def items_nombre_valor(texto):
    """«nombre … valor» en una línea sin '|': texto y al final un monto de >= 3 dígitos."""
    out = []
    for l in texto.splitlines():
        if "|" in l or NO.search(norm(l)): continue
        m = re.match(rf"^\W*(?:\d{{1,3}}\s+)?(?P<n>[^\W\d_][^\d$]{{2,}}?)\s+(?P<v>{NUM})\s*$", l)
        if m and 100 <= monto(m.group("v")) < TOPE: out.append(dict(nombre=m.group("n").strip(), valor=monto(m.group("v"))))
    return out


def items_de(texto):
    return items_tabla(texto) or items_nombre_valor(texto)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--mes", default="2026-09"); ap.add_argument("--ver", type=int, default=0)
    a = ap.parse_args()
    lib = json.load(open(BASE / "datos" / "libro.json", encoding="utf-8"))
    fac = [p for d, x in lib.items() if d.startswith(a.mes) for p in x.get("documentos", []) if p.get("tipo") == "factura" and not p.get("dup_de")]
    legibles = [p for p in fac if len((p.get("texto") or "").strip()) > 40]
    con = cuadran = 0; sin = []; mal = []
    for p in fac:
        its = items_de(p.get("texto", "")); tot = p.get("valor") or 0
        if its:
            con += 1
            s = sum(i["valor"] for i in its)
            if tot and abs(s - tot) <= 0.01 * tot: cuadran += 1
            else: mal.append((p.get("tercero"), tot, s, len(its)))
        else: sin.append((p.get("tercero"), tot))
    n = len(fac)
    print(f"facturas {a.mes}: {n}\n  con >= 1 ítem con valor: {con} ({100*con/max(n,1):.0f} %)\n  suman el total +-1 %: {cuadran} ({100*cuadran/max(n,1):.0f} %)")
    print(f"  con texto legible: {len(legibles)}")
    print(f"  sin ítems: {len(sin)} · con ítems que no cuadran: {len(mal)}")
    for t in sin[:a.ver]: print("  SIN", t)
    for t in mal[:a.ver]: print("  NO CUADRA (tercero, total, suma, n)", t)


if __name__ == "__main__": main()
