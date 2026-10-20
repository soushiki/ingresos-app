"""Extracto bancario (01c #5, T1): reglas en JSON + clasificar(). Fitness de ADR-013 contra la hoja MOVIMIENTOS (datos reales, fuera del repo)."""
import collections
import copy
import json
import re
import tempfile
from pathlib import Path

from parser_module.contable import extracto as X

fallos = []
def chk(cond, msg):
    print(("✓ " if cond else "✗ ") + msg)
    if not cond: fallos.append(msg)

AQUI = Path(__file__).parent
REGLAS = X.cargar_reglas()

# --- cargar_reglas ---
chk(REGLAS["ventana_factura_dias"] == 3 and REGLAS["reglas"], "las reglas cargan con ventana_factura_dias = 3")
chk(all(c["por_confirmar"] is True and c["fuente"].strip() for c in REGLAS["cuentas"].values()), "toda cuenta lleva fuente y por_confirmar: true (P2, regulado)")
chk({"gmf", "rendimientos", "por_cobrar_rappi", "banco", "puente"} <= set(REGLAS["cuentas"]), "cuentas del diseño §8: gmf, rendimientos, por_cobrar_rappi, banco, puente")

def con(cambio):
    r = copy.deepcopy(REGLAS); cambio(r)
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "r.json"; p.write_text(json.dumps(r), encoding="utf8")
        try: X.cargar_reglas(p); return None
        except X.ReglasInvalidas as e: return str(e)

chk(con(lambda r: None) is None, "reglas sin tocar: válidas")
chk(con(lambda r: r["reglas"][0].update(prefijo="  ")) is not None, "prefijo vacío → ReglasInvalidas")
chk(con(lambda r: r["reglas"][0].update(signo="*")) is not None, "signo raro → ReglasInvalidas")
chk(con(lambda r: r["reglas"][0].update(destino="casilla:inventada")) is not None, "casilla desconocida → ReglasInvalidas")
chk(con(lambda r: r["reglas"][0].update(destino="cuenta:inventada")) is not None, "cuenta desconocida → ReglasInvalidas")
chk(con(lambda r: r["reglas"][0].update(concepto="")) is not None, "concepto vacío → ReglasInvalidas")
chk(con(lambda r: r["cuentas"]["gmf"].update(codigo="99999999")) is not None, "código fuera del plan y de los puentes → ReglasInvalidas")
chk(con(lambda r: r["cuentas"]["gmf"].update(codigo="5315")) is not None, "código que no tiene 8 dígitos → ReglasInvalidas")
chk(con(lambda r: r["cuentas"]["gmf"].pop("fuente")) is not None, "cuenta sin fuente → ReglasInvalidas")
chk(con(lambda r: r["cuentas"]["gmf"].update(por_confirmar="si")) is not None, "por_confirmar no booleano → ReglasInvalidas")
chk(con(lambda r: r.update(ventana_factura_dias=0)) is not None, "ventana_factura_dias = 0 → ReglasInvalidas")
chk(con(lambda r: r.update(sin_tercero=[""])) is not None, "sin_tercero con un prefijo vacío → ReglasInvalidas")
with tempfile.TemporaryDirectory() as d:
    p = Path(d) / "r.json"; p.write_text("{no es json", encoding="utf8")
    try: X.cargar_reglas(p); ok = False
    except X.ReglasInvalidas: ok = True
chk(ok, "JSON roto → ReglasInvalidas (no un error crudo)")

# --- clasificar (pura) ---
def una(desc, valor):
    return X.clasificar([{"descripcion": desc, "valor": valor}], REGLAS)[0]

casos = [("IMPTO GOBIERNO 4X1000", -610, "GMF", "cuenta:gmf", REGLAS["cuentas"]["gmf"]["codigo"]),
         ("PAGO LLAVE PEDRO PRUE", 18000, "PAGO LLAVE", "casilla:llave", ""),
         ("ABONO NETO MASTER", 85000, "ABONO MASTER", "casilla:tarjetas", ""),
         ("ABONO NETO VISA", 1000, "ABONO VISA", "casilla:tarjetas", ""),
         ("ABONO NETO AMEX", 1000, "ABONO AMEX", "casilla:tarjetas", ""),
         ("PAGO QR CLIENTE UNO", 64000, "RECAUDO QR", "casilla:qr", ""),
         ("PAGO QR BOLD", -64000, "PAGO QR", "revisar", ""),
         ("PAGO PSE PROVEEDOR EJEMPLO SAS", -300000, "PAGO PSE", "revisar", ""),
         ("PAGO INTERBANC RAPPI SAS", 50000, "PAGO RAPPI", "casilla:rappi", ""),
         ("ABONO INTERESES AHORROS", 5, "RENDIMIENTOS", "cuenta:rendimientos", REGLAS["cuentas"]["rendimientos"]["codigo"]),
         ("TRANSFERENCIAS A NEQUI", -70000, "TRANSFER NEQUI CR", "revisar", ""),
         ("TRANSFERENCIA CTA SUC VIRTUAL", -150000, "TRANSFER CR", "revisar", ""),
         ("TRANSF A juan prueba", -70000, "TRANSFER CR", "revisar", ""),
         ("COMPRA INTL GOOGLE", -12000, "COMPRA", "revisar", "")]
for d, v, conc, dest, cta in casos:
    r = una(d, v)
    chk((r["concepto"], r["destino"], r["cuenta"], r["origen"]) == (conc, dest, cta, "regla") and not r["avisos"], f"«{d}» {v:+} → {conc} / {dest}")

chk(una("pago llave  carlos", 5000)["concepto"] == "PAGO LLAVE", "minúsculas y espacios dobles no estorban")
chk(una("PAGÓ LLAVE X", 5000)["concepto"] == "PAGO LLAVE", "tildes no estorban")
r = una("COBRO NUEVO DEL BANCO", -5000)
chk((r["concepto"], r["destino"], r["origen"]) == (X.SIN_CONCEPTO, "revisar", "") and r["avisos"], "nada encaja → SIN CONCEPTO + revisar + aviso (no se descarta)")
r = una("ABONO NETO VISA", -5000)
chk(r["concepto"] == X.SIN_CONCEPTO and r["destino"] == "revisar" and any("signo inesperado" in a for a in r["avisos"]), "abono con signo negativo → aviso «signo inesperado» (R7)")
r = una("IMPTO GOBIERNO 4X1000", 610)
chk(r["destino"] == "revisar" and any("signo inesperado" in a for a in r["avisos"]), "GMF con signo positivo → «signo inesperado»")
chk(una("PAGO QR X", 0)["destino"] == "revisar", "valor 0 no se clasifica en silencio")
entrada = [{"descripcion": "PAGO LLAVE X", "valor": 1000, "avisos": ["previo"]}]
copia = copy.deepcopy(entrada); sal = X.clasificar(entrada, REGLAS)
chk(entrada == copia and sal[0]["avisos"] == ["previo"] and sal is not entrada, "clasificar es pura: no toca la entrada y conserva los avisos previos")
chk(len(X.clasificar([{"descripcion": "A", "valor": 1}] * 7, REGLAS)) == 7, "una salida por cada línea (nunca descarta)")

# --- ADR-013: ningún código PUC en extracto.py ---
fuente = (AQUI / "parser_module" / "contable" / "extracto.py").read_text(encoding="utf8")
chk(not re.findall(r"\b[0-9]{8}\b", fuente), "ADR-013: código PUC fijo en extracto.py (ninguno)")

# --- ADR-013: reglas contra la hoja MOVIMIENTOS (datos reales; se omite si falta) ---
# Errores de la hoja etiquetada a mano que el usuario acepta (concepto escrito mal, no una regla mal):
ETIQUETA_MAL = {"TRABSFER CR": "TRANSFER CR", "RAPPI": "PAGO RAPPI"}
# Excepciones aceptadas (desacuerdos que se quedan a propósito; ambas van a revisión de todos modos):
#  - un ingreso por TRANSFERENCIA CTA SUC (la regla solo conoce la salida: signo inesperado → SIN CONCEPTO → revisar);
#  - un «TRANSF A <nombre>» que la hoja marcó NEQUI y otros iguales marcó CR (criterio manual inconsistente).
_ORA = AQUI.parent / "data" / "extracto_oraculo.json"   # casos reales (cifras y nombres): junto al xlsx, fuera del repo
_o = __import__("json").loads(_ORA.read_text(encoding="utf8")) if _ORA.exists() else {}
ETIQUETA_MAL.update(_o.get("etiqueta_mal", {}))
EXCEPCIONES = {tuple(e) for e in _o.get("excepciones", [])}
XLSX = AQUI.parent / "data" / "202609 - Movimientos banco 1-30Sept2026.xlsx"
if not XLSX.exists():
    print(f"- OMITIDO: falta {XLSX} (datos reales, no van al repo); el fitness de ADR-013 contra MOVIMIENTOS no corrió")
else:
    from openpyxl import load_workbook
    wb = load_workbook(XLSX, read_only=True, data_only=True)
    def llave(f, d, v): return (f.date(), re.sub(r"\s+", " ", str(d)).strip().upper(), round(float(v)))
    hoja = [r for r in wb["Hoja 1"].iter_rows(min_row=2, values_only=True) if r[0]]
    oraculo = collections.defaultdict(collections.deque)
    for r in wb["MOVIMIENTOS"].iter_rows(min_row=6, values_only=True):
        if r[0] is not None and hasattr(r[0], "day") and r[4] is not None:
            oraculo[llave(r[0], r[1], r[4])].append(str(r[2]).strip())
    lineas = [{"descripcion": str(r[1]), "valor": r[3], "k": llave(r[0], r[1], r[3])} for r in hoja]
    chk(len(lineas) == 513, f"Hoja 1 trae 513 líneas ({len(lineas)})")
    res = X.clasificar(lineas, REGLAS)
    ok, sin_par, malos = 0, 0, []
    for ln in res:
        cola = oraculo.get(ln["k"])
        if not cola: sin_par += 1; continue
        esperado = cola.popleft(); esperado = ETIQUETA_MAL.get(esperado, esperado)
        if ln["concepto"] == esperado: ok += 1
        else: malos.append((ln["descripcion"], round(ln["valor"]), ln["concepto"], esperado))
    total = ok + len(malos)
    for m in malos: print(f"  desacuerdo{' (aceptado)' if m in EXCEPCIONES else ''}: {m[0]!r} {m[1]:+} → regla {m[2]!r}, hoja {m[3]!r}")
    print(f"  {ok}/{total} coinciden; {len(malos)} desacuerdos; {sin_par} sin par en MOVIMIENTOS")
    chk(set(malos) <= EXCEPCIONES, "todo desacuerdo con la hoja es una excepción aceptada")
    chk(sin_par == 0, "toda línea de Hoja 1 tiene su par en MOVIMIENTOS (fecha, descripción, valor)")
    chk(total and ok / total >= 0.98, f"ADR-013: reglas por debajo del 98 % ({ok}/{total} = {ok / max(total, 1):.1%})")
    sin = [ln for ln in res if ln["concepto"] == X.SIN_CONCEPTO]
    chk(len(sin) <= 1 and all(ln["avisos"] for ln in sin), f"septiembre real: solo {len(sin)} línea SIN CONCEPTO, con aviso (va a revisión)")

print(f"\n{len(fallos)} fallos" if fallos else "\nTODO OK")
raise SystemExit(1 if fallos else 0)
