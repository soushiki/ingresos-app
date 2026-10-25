"""Mina el Excel manual (hojas MOVIMIENTOS de cada mes) y escribe parser_module/contable/modelo_manual.json (ADR-020).
El modelo lleva solo palabra, proveedor y cuenta (+ fuente «julio fila 631»): sin valores, fechas ni nombres de personas (N5).
Uso: python herramientas/minar_manual.py [--meses jun,jul,ago] [--hasta 2026-08] [--salida ruta.json] [--manual ruta.xlsx]
Sin --meses/--hasta escribe el modelo de producción; con filtro hay que dar --salida (para medir N1 sin pisarlo)."""
from __future__ import annotations
import argparse, datetime as dt, json, re, sys
from collections import Counter, defaultdict
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
from parser_module.numeros import norm

MANUAL = Path(r"D:\Claude\image_to_text\data\Reporte contable 2026 actualizado 10-16-2026.xlsx")
SALIDA = APP / "parser_module" / "contable" / "modelo_manual.json"
TERCEROS = APP / "parser_module" / "contable" / "terceros_cuentas.json"   # local, en .gitignore: aquí sí van las personas (N5)
MIN_VECES, MIN_PCT = 2, 0.80
GENERICOS = {"consumidor final", "cuantias menores", "caja", ""}
VACIAS = set("""pago pagos compra compras del las los con por para una sus que factura facturas fact recibo recibos abono junio julio agosto
 septiembre sept octubre semana dia dias mes quincena nro num total valor otros otro varios varias via traves pedido cta cuenta ahorros bancolombia
 recaudos recuados recaudo dinero""".split())
# cuentas cuyo tercero es una persona (nómina 5105, capital 31, cuentas por pagar a socios/empleados 25, anticipos 1330)
CUENTAS_PERSONA = ("5105", "31", "25", "1330")
NO_GASTO = ("11", "41", "31", "15", "42")   # caja/banco, ingresos, capital, aportes: no clasifican un gasto


def fuente(hoja: str, fila: int) -> str: return f"{hoja.split()[1].lower()} fila {fila}"
def toks(s: str) -> list[str]:
    return [t for t in re.findall(r"[a-z]{3,20}", norm(s)) if t not in VACIAS and not re.fullmatch(r"[a-f]+", t)]   # sin pedazos de ID


def pares(desc: str, pers: set[str]) -> set[str]:
    """bigramas de palabras contiguas (se conservan «pago», «dia»…); una persona o un pedazo de ID corta la cadena."""
    out, ant = set(), None
    for t in re.findall(r"[a-z]{3,20}", norm(desc)):
        if t in pers or re.fullmatch(r"[a-f]+", t): ant = None; continue
        if ant: out.add(f"{ant} {t}")
        ant = t
    return out


def leer_filas(ruta: Path = MANUAL) -> list[dict]:
    import openpyxl
    wb = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
    filas = []
    for hoja in [n for n in wb.sheetnames if n.startswith("MOVIMIENTOS")]:
        for i, r in enumerate(wb[hoja].iter_rows(min_row=9, max_col=11, values_only=True), 9):
            if not isinstance(r[0], dt.datetime) or not r[1]: continue
            cod = str(r[1]).split(".")[0].strip()
            if not cod.isdigit(): continue
            num = lambda v: float(v) if isinstance(v, (int, float)) else 0.0
            filas.append(dict(hoja=hoja, fila=i, mes=r[0].date().isoformat()[:7], codigo=cod, tercero=str(r[3] or "").strip(),
                              desc=str(r[4] or "").strip(), deb=num(r[5]), cre=num(r[6]), reporta=str(r[8] or "").strip()))
    return filas


NOMINA = set("""nomina sueldo sueldos salario salarios quincena turno turnos prima cesantias vacaciones liquidacion dotacion auxilio horas extras
 aporte aportes inicial capital adelanto anticipo prestamo pagos pago""".split())


def personas(filas: list[dict]) -> set[str]:
    """tokens de nombres de personas: terceros de nómina/capital/socios, quien «reporta», y las palabras de la descripción de esas filas
    que no son de nómina ni aparecen en filas de otras cuentas («nomina yorly» → yorly)."""
    p, en_persona, en_otras = set(), set(), set()
    for x in filas:
        if x["codigo"].startswith(CUENTAS_PERSONA):
            p.update(re.findall(r"[a-z]{3,}", norm(x["tercero"]))); en_persona.update(toks(x["desc"]))
        elif not x["codigo"].startswith(NO_GASTO): en_otras.update(toks(x["desc"]))   # el pago por banco repite el nombre
        p.update(re.findall(r"[a-z]{3,}", norm(x["reporta"])))
    return p | (en_persona - NOMINA - en_otras)


def minar(filas: list[dict], meses: set[str] | None = None, hasta: str | None = None) -> dict:
    """meses: prefijos de 3 letras de la hoja («jun»); hasta: «2026-08» incluye ese mes."""
    pers = personas(filas)   # los nombres se aprenden de TODAS las filas, aunque el filtro las deje fuera
    usadas = [x for x in filas if (not meses or norm(x["hoja"].split()[1])[:3] in meses) and (not hasta or x["mes"] <= hasta)]
    gastos = [x for x in usadas if x["deb"] > 0 and not x["codigo"].startswith(NO_GASTO) and "recaud" not in norm(x["desc"]) and "recuad" not in norm(x["desc"])]
    lex, prov, vec, big = defaultdict(Counter), defaultdict(Counter), {}, defaultdict(Counter)
    for x in gastos:
        ts = {t for t in toks(x["desc"]) if t not in pers}
        for t in ts: lex[t][x["codigo"]] += 1
        for b in pares(x["desc"], pers): big[b][x["codigo"]] += 1
        t = " ".join(norm(x["tercero"]).split())
        if t and t not in GENERICOS and not re.search(r"\d{4,}", t) and not x["codigo"].startswith(CUENTAS_PERSONA) and not (set(re.findall(r"[a-z]{3,}", t)) & pers):
            prov[t][x["codigo"]] += 1
        txt = " ".join(t for t in toks(x["desc"]) if t not in pers)
        if txt: vec.setdefault(txt, []).append((x["codigo"], fuente(x["hoja"], x["fila"])))

    def mayoria(c: Counter):
        cta, n = c.most_common(1)[0]; tot = sum(c.values()); return cta, n, tot
    lexico, proveedores, vecinos, bigramas = {}, {}, [], {}
    for t, c in sorted(big.items()):
        cta, n, tot = mayoria(c)
        if tot >= MIN_VECES and n / tot >= MIN_PCT: bigramas[t] = dict(cuenta=cta, n=n, de=tot)
    for t, c in sorted(lex.items()):
        cta, n, tot = mayoria(c)
        if tot >= MIN_VECES and n / tot >= MIN_PCT: lexico[t] = dict(cuenta=cta, n=n, de=tot)
    for t, c in sorted(prov.items()):
        cta, n, tot = mayoria(c)
        if tot >= MIN_VECES and n / tot >= MIN_PCT: proveedores[t] = dict(cuenta=cta, n=n, de=tot)
    for txt, lst in sorted(vec.items()):
        c = Counter(a for a, _ in lst); cta, n, tot = mayoria(c)
        if n / tot >= MIN_PCT: vecinos.append(dict(texto=txt, cuenta=cta, fuente=next(f for a, f in lst if a == cta)))
    return dict(version=1, meses=sorted({x["mes"] for x in usadas}), lexico=lexico, bigramas=bigramas, proveedores=proveedores, vecinos=vecinos)


def terceros(filas: list[dict], meses: set[str] | None = None, hasta: str | None = None) -> dict:
    """terceros que son personas (nómina, socios, quien reporta) → cuenta de mayoría (≥ 2, ≥ 80 %). Solo para terceros_cuentas.json local."""
    pers = personas(filas); c = defaultdict(Counter)
    for x in filas:
        if meses and norm(x["hoja"].split()[1])[:3] not in meses or hasta and x["mes"] > hasta: continue
        t = " ".join(norm(x["tercero"]).split())
        if x["deb"] > 0 and t and t not in GENERICOS and not re.search(r"\d{4,}", t) and not x["codigo"].startswith(NO_GASTO)            and (x["codigo"].startswith(CUENTAS_PERSONA) or set(re.findall(r"[a-z]{3,}", t)) & pers):
            c[t][x["codigo"]] += 1
    out = {}
    for t, cn in sorted(c.items()):
        cta, n = cn.most_common(1)[0]; tot = sum(cn.values())
        if tot >= MIN_VECES and n / tot >= MIN_PCT: out[t] = dict(cuenta=cta, n=n, de=tot)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--meses", help="hojas a usar, 3 letras: jun,jul,ago")
    ap.add_argument("--hasta", help="último mes incluido, AAAA-MM")
    ap.add_argument("--salida", type=Path); ap.add_argument("--manual", type=Path, default=MANUAL)
    a = ap.parse_args(argv)
    if (a.meses or a.hasta) and not a.salida: ap.error("con --meses/--hasta indica --salida (no se pisa el modelo de producción)")
    meses = {m.strip().lower()[:3] for m in a.meses.split(",")} if a.meses else None
    filas = leer_filas(a.manual)
    modelo = minar(filas, meses, a.hasta)
    destino = a.salida or SALIDA
    destino.write_text(json.dumps(modelo, ensure_ascii=False, indent=1), encoding="utf8")
    if not a.salida:   # modelo de producción: las personas van aparte, a un archivo local
        TERCEROS.write_text(json.dumps(terceros(filas), ensure_ascii=False, indent=1), encoding="utf8")
    print(f"{destino}: {len(modelo['lexico'])} palabras · {len(modelo['proveedores'])} proveedores · {len(modelo['vecinos'])} vecinos · {len(modelo['bigramas'])} bigramas · meses {modelo['meses']}")


if __name__ == "__main__": main()
