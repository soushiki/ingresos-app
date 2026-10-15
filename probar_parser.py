"""Prueba del módulo 2.
    python probar_parser.py                 → corre los ejemplos y compara con lo esperado
    python probar_parser.py texto.txt       → muestra cómo se interpreta un texto (salida del módulo 1)
"""
import json, sys
from pathlib import Path
from parser_module import CLAVES, NOMBRE, Config, parsear

ICONO = {"ok": "✓", "revisar": "⚠", "faltante": "✗"}


def mostrar(c):
    print(f"  fecha: {c.fecha or '—'}")
    for k in c.orden:
        f = c.campos[k]
        v = "(no aparece)" if f.estado == "faltante" else ("(sin valor)" if f.valor is None else f"{f.valor:,}".replace(",", "."))
        extra = f"   ← {'; '.join(f.razones)}" if f.razones else ""
        print(f"  {ICONO[f.estado]} {c.nombres[k]:<20} {v:<14}{extra}")
    for d in c.desconocidas: print(f"  ? etiqueta no reconocida: «{d['etiqueta']}» = {d['valor']:,}".replace(",", "."))
    for n in c.notas: print(f"  · nota: {n}")
    for a in c.advertencias: print(f"  ! {a}")


def ejemplos():
    base = Path(__file__).parent / "parser_module" / "ejemplos"
    esp = json.loads((base / "esperados.json").read_text(encoding="utf8"))
    ok_t = tot_t = 0
    for nombre, e in esp.items():
        c = parsear((base / nombre).read_text(encoding="utf8"), Config(), anio=2026, fuente=nombre)
        fallos = []
        if "fecha" in e and c.fecha != e["fecha"]: fallos.append(f"fecha {c.fecha} ≠ {e['fecha']}")
        for k, v in e["valores"].items():
            tot_t += 1
            if c.campos[k].valor == v: ok_t += 1
            else: fallos.append(f"{k}: {c.campos[k].valor} ≠ {v}")
        for k in e.get("faltantes", []):
            if c.campos[k].estado != "faltante": fallos.append(f"{k} debía faltar")
        for k in e.get("revisar", []):
            if c.campos[k].estado == "ok": fallos.append(f"{k} debía marcarse «revisar»")
        if e.get("todos_ok") and c.por_revisar(): fallos.append("debían salir todos OK: " + ", ".join(c.por_revisar()))
        for et, v in e.get("desconocidas", []):
            if not any(d["etiqueta"] == et and d["valor"] == v for d in c.desconocidas): fallos.append(f"falta desconocida {et}={v}")
        print(f"{'✓' if not fallos else '✗'} {nombre}" + ("" if not fallos else "\n    " + "\n    ".join(fallos)))
    print(f"\nValores correctos: {ok_t}/{tot_t}")
    return ok_t == tot_t


if __name__ == "__main__":
    if len(sys.argv) > 1:
        mostrar(parsear(Path(sys.argv[1]).read_text(encoding="utf8"), Config.cargar("alias_negocio.json")))
    else:
        sys.exit(0 if ejemplos() else 1)
