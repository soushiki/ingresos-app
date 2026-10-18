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


def venta_campos():
    """T2 / R1: parse_venta saca items, subtotal, pagado, cambio y hora; acierto de subtotal en septiembre (libro.json) ≥ 95 %."""
    from parser_module.contable.documentos import parse_venta
    t = ("RECIBO #: 85999\nFecha de Venta: 16/09/2026 8:01:37 p. m.\n| Descripcion | Cant | Valor |\n| SOL | 2 | 14,000 |\n| COMBO AMOR | 1 | 55,000 |\n"
         "SUBTOTAL CONSUMO $69,000\n**TOTAL CONSUMO>> $69000\nDESCUENTO $\n*TOTAL A PAGAR> $69,000\nPROPINA $6,900\nPAGADO $80,000\nPAGA CON EFECTIVO $80,000\nCAMBIO $4,100\n")
    d = parse_venta(t); fallos = []
    esp = dict(items=[dict(cant=2, nombre="SOL", valor=14000), dict(cant=1, nombre="COMBO AMOR", valor=55000)], subtotal=69000, pagado=80000, cambio=4100, hora="20:01")
    for k, v in esp.items():
        if d.get(k) != v: fallos.append(f"{k}: {d.get(k)} ≠ {v}")
    sin = parse_venta("RECIBO #: 85998\nFecha de Venta: 5/09/2026 9:30:00 a. m.\nSUBTOTAL CONSUMO $10,000\n*TOTAL A PAGAR> $10,000\nPAGADO $10,000\nPAGA CON EFECTIVO $10,000\n")
    if (sin["items"], sin["cambio"], sin["hora"]) != ([], 0, "09:30"): fallos.append(f"sin ítems/cambio: {sin['items']} {sin['cambio']} {sin['hora']}")
    if parse_venta("RECIBO #: 85997\nPAGADO $5,000\n")["hora"] != "": fallos.append("sin hora debía dar vacío")
    libro = Path(__file__).parent / "datos" / "libro.json"
    if libro.exists():
        docs = [o for x in json.loads(libro.read_text(encoding="utf8")).values() if isinstance(x, dict) for z in x.values() if isinstance(z, list) for o in z
                if isinstance(o, dict) and o.get("tipo") == "venta" and str(o.get("fecha", "")).startswith("2026-09") and "SUBTOTAL" in o.get("texto", "").upper()]
        ok = sum(parse_venta(o["texto"])["subtotal"] in (o["consumo"], o["consumo"] + o["descuento"]) for o in docs)
        print(f"  subtotal septiembre: {ok}/{len(docs)} = {ok / max(1, len(docs)):.1%}")
        if docs and ok / len(docs) < 0.95: fallos.append("acierto de subtotal < 95 %")
    print(f"{'✓' if not fallos else '✗'} parse_venta: items, subtotal, pagado, cambio, hora" + ("" if not fallos else "\n    " + "\n    ".join(fallos)))
    return not fallos


if __name__ == "__main__":
    if len(sys.argv) > 1:
        mostrar(parsear(Path(sys.argv[1]).read_text(encoding="utf8"), Config.cargar("alias_negocio.json")))
    else:
        sys.exit(0 if (ejemplos() & venta_campos()) else 1)
