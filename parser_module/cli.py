"""Uso:  python -m parser_module.cli salida/            (carpeta con .txt o resultados.jsonl del módulo 1)
        python -m parser_module.cli planilla.txt --aprender "gas=cajam"
"""
import argparse, csv, json, sys
from collections import Counter
from pathlib import Path
from .config import Config
from .esquema import Esquema
from .parser import _Vocab, parsear

ICONO = {"ok": "✓", "revisar": "⚠", "faltante": "✗"}


def leer(entradas):
    out = []
    for e in map(Path, entradas):
        if e.is_dir():
            j = e / "resultados.jsonl"
            if j.is_file(): out += leer([j])
            else: out += [(t.stem, t.read_text(encoding="utf8")) for t in sorted(e.glob("*.txt"))]
        elif e.suffix == ".jsonl":
            for l in e.read_text(encoding="utf8").splitlines():
                if l.strip():
                    d = json.loads(l)
                    if d.get("ok", True) and d.get("text"): out.append((Path(d["source"]).stem, d["text"]))
                    else: print(f"(omitida por error de lectura: {d.get('source')})", file=sys.stderr)
        elif e.is_file():
            out.append((e.stem, e.read_text(encoding="utf8")))
    return out


def main():
    ap = argparse.ArgumentParser(description="Texto del OCR → campos del cierre de caja")
    ap.add_argument("entradas", nargs="+")
    ap.add_argument("-o", "--out", default="cierres")
    ap.add_argument("--config", default="alias_negocio.json")
    ap.add_argument("--anio", type=int, default=None)
    ap.add_argument("--aprender", action="append", default=[], metavar="ETIQUETA=CAMPO",
                    help="enseña una etiqueta nueva (usa la clave de la columna)")
    ap.add_argument("--esquema", default="esquema.json", help="columnas del negocio (JSON); si no existe se usan las 12 originales")
    ap.add_argument("--llm", action="store_true", help="completa campos faltantes con el modelo local (opcional)")
    a = ap.parse_args()

    esq = Esquema.cargar(a.esquema)
    cfg = Config.cargar(a.config, esq); cfg.ruta = a.config
    for par in a.aprender:
        et, _, campo = par.partition("=")
        try: cfg.aprender(et.strip(), campo.strip()); print(f"Aprendido: «{et.strip()}» → {campo.strip()}")
        except ValueError as e: sys.exit(str(e))
    items = leer(a.entradas)
    if not items: sys.exit("No encontré textos para procesar.")
    V = _Vocab(cfg)
    cierres, nuevas = [], Counter()
    for nombre, texto in items:
        c = parsear(texto, cfg, a.anio, nombre, V)
        if a.llm:
            from .llm_fallback import completar
            completar(c)
        cierres.append(c)
        print(f"\n━━ {nombre} · {c.fecha or 'sin fecha'}")
        for k in c.orden:
            f = c.campos[k]
            v = "(no aparece)" if f.estado == "faltante" else "(sin valor)" if f.valor is None else f"{f.valor:,}".replace(",", ".")
            print(f"  {ICONO[f.estado]} {c.nombres[k]:<20} {v:<14}{'  ← ' + '; '.join(f.razones) if f.razones else ''}")
        for d in c.desconocidas: nuevas[d["etiqueta"]] += 1
        for w in c.advertencias: print(f"  ! {w}")
    out = Path(a.out); out.mkdir(exist_ok=True)
    (out / "cierres.json").write_text(json.dumps([c.to_dict() for c in cierres], ensure_ascii=False, indent=1), encoding="utf8")
    with open(out / "cierres.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["Archivo", "Fecha"] + [esq.nombres[k] for k in esq.claves] + ["Campos por revisar", "Notas"])
        for c in cierres:
            w.writerow([c.fuente, c.fecha or ""] + [c.valor(k) for k in esq.claves]
                       + [", ".join(c.nombres[k] for k in c.por_revisar()), " | ".join(c.notas)])
    rev = sum(len(c.por_revisar()) for c in cierres)
    print(f"\n{len(cierres)} cierres · {rev} campos por revisar → {out.resolve()}")
    if nuevas:
        print("\nEtiquetas no reconocidas (enséñalas con --aprender \"etiqueta=campo\"):")
        for et, n in nuevas.most_common(): print(f"  «{et}» ×{n}")


if __name__ == "__main__":
    main()
