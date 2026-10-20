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

# --- T2: leer_xlsx ---
import datetime as _dt
import io
import zipfile
from openpyxl import Workbook

def xlsx(filas, hoja="Hoja 1", cab=("Fecha", "Descripción", "Referencia", "Valor")):
    wb = Workbook(); ws = wb.active; ws.title = hoja
    if cab: ws.append(list(cab))
    for f in filas: ws.append(list(f))
    b = io.BytesIO(); wb.save(b); return b.getvalue()

def falla(datos):
    try: X.leer_xlsx(datos); return None
    except X.ExtractoInvalido as e: return str(e)

D = _dt.datetime(2026, 9, 23, 5, 0)
L = X.leer_xlsx(xlsx([(D, "PAGO QR  X", "009", 64000), (D, "IMPTO GOBIERNO 4X1000", None, -2592.4),
                      (D, "PAGO QR  X", "009", 64000), (D, "PAGO QR  X", "009", 64000), (None, None, None, None)]))
chk(len(L) == 4, "leer_xlsx salta las filas totalmente vacías")
chk(len(L) == 4 and L[0]["fecha"] == "2026-09-23" and isinstance(L[0]["valor"], int), "fecha solo con el día (ISO) y valor int")
chk(L[1]["valor"] == -2592 and L[1]["referencia"] == "", "valor decimal → int con signo; referencia vacía → ''")
chk([l["ocurrencia"] for l in L] == [1, 1, 2, 3], "líneas idénticas reciben ocurrencias 1, 2, 3 en orden")
chk(len({l["clave"] for l in L}) == 4 and all(re.fullmatch(r"[0-9a-f]{16}", l["clave"]) for l in L), "claves distintas, sha1[:16]")
L2 = X.leer_xlsx(xlsx([(D, "pago qr x", "009", 64000)]))
chk(L2[0]["clave"] == L[0]["clave"], "la clave normaliza la descripción (misma línea, misma clave)")
chk(X.leer_xlsx(xlsx([(D.replace(hour=9), "PAGO QR  X", "009", 64000)]))[0]["clave"] == L[0]["clave"], "la hora no cambia la clave")
chk(falla(xlsx([(D, "A", "", 1)], hoja="Otra")) and "Hoja 1" in falla(xlsx([(D, "A", "", 1)], hoja="Otra")), "otra hoja → ExtractoInvalido (dice «Hoja 1»)")
chk(falla(xlsx([(D, "A", "", 1)], cab=("Fecha", "Texto", "Referencia", "Valor"))) is not None, "otras columnas → ExtractoInvalido")
chk(falla(xlsx([(D, "A", "", 1)], cab=("Fecha", "Descripción", "Referencia"))) is not None, "faltan columnas → ExtractoInvalido")
chk(falla(xlsx([("no fecha", "A", "", 1)])) is not None, "fecha ilegible → ExtractoInvalido")
chk(falla(xlsx([(D, "A", "", "mucho")])) is not None, "valor no numérico → ExtractoInvalido")
chk(falla(xlsx([(D, "", "", 5)])) is not None, "descripción vacía → ExtractoInvalido")
chk(falla(b"no soy un zip") is not None, "bytes cualquiera → ExtractoInvalido")
bz = io.BytesIO()
with zipfile.ZipFile(bz, "w") as z: z.writestr("a.txt", "hola")
chk(falla(bz.getvalue()) is not None, "un ZIP que no es xlsx → ExtractoInvalido")
chk(falla(b"") is not None, "archivo vacío → ExtractoInvalido")
chk(falla(xlsx([(D, f"L{i}", "", i) for i in range(1, 5002)])) and "5000" in falla(xlsx([(D, f"L{i}", "", i) for i in range(1, 5002)])), "más de 5 000 filas → ExtractoInvalido con el tope")
chk(len(X.leer_xlsx(xlsx([(D, f"L{i}", "", i) for i in range(1, 5001)]))) == 5000, "5 000 filas exactas: pasa")
chk(falla(b"x" * (5 * 1024 * 1024 + 1)) and "5 MB" in falla(b"x" * (5 * 1024 * 1024 + 1)), "más de 5 MB → ExtractoInvalido")

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
    # T2: el archivo real por leer_xlsx
    LR = X.leer_xlsx(XLSX.read_bytes())
    chk(len(LR) == 513, f"T2: leer_xlsx del real da 513 líneas ({len(LR)})")
    chk(sum(l["valor"] for l in LR) == sum(round(float(r[3])) for r in hoja), "T2: suma de valores = suma de Valor de Hoja 1")
    chk(len({l["clave"] for l in LR}) == 513, "T2: 513 claves distintas")

# --- T3: bloque 5 «Extracto» en construir (R6, R8, S2, S5) ---
import io
from openpyxl import load_workbook
from parser_module.contable import asientos as A, exportar as E
def lin(desc, valor, n=[0]):
    n[0] += 1
    return dict(clave=f"k{n[0]:015d}", fecha="2026-09-25", descripcion=desc, referencia="", valor=valor, ocurrencia=1, imp="i1")
DIA = X.clasificar([lin("IMPTO GOBIERNO 4X1000", -610), lin("ABONO INTERESES AHORROS", 37), lin("PAGO INTERBANC RAPPI SAS", 250000),
                    lin("TRANSF A ANA PRUEBA", -120000), lin("PAGO QR CLIENTE", 64000), lin('=HYPERLINK("x")', -5000)], REGLAS)
DIA.append(dict(lin("PAGO INTERBANC RAPPI SAS", 90000), concepto="PAGO RAPPI", destino="cuenta:por_cobrar_rappi",
                cuenta=REGLAS["cuentas"]["por_cobrar_rappi"]["codigo"], origen="usuario", avisos=[], tercero="Rappi"))
r = A.construir("2026-09-25", [], {}, extracto=DIA)
fx = [f for f in r["filas"] if f["grupo"] == "Extracto"]
C = {k: c["codigo"] for k, c in REGLAS["cuentas"].items()}
lados = lambda x: {(f["codigo"], f["debito"], f["credito"]) for f in fx if f["docs"] == [x["clave"]]}
chk(r["debito"] == r["credito"] > 0 and r["diferencia"] == 0, f"T3: día sin papeles (documentos: []) con extracto cuadra ({r['debito']} = {r['credito']})")
chk(len(fx) == 2 * 5 and all(f["grupo"] == "venta" for f in r["filas"] if f not in fx), f"T3: 5 líneas cuenta/revisar → 10 filas «Extracto» ({len(fx)}); las casillas van a venta (T6)")
chk(lados(DIA[0]) == {(C["gmf"], 610, 0), (C["banco"], 0, 610)}, "T3 R6: GMF débito 53152001 / crédito Bancos por el valor exacto")
chk(lados(DIA[1]) == {(C["banco"], 37, 0), (C["rendimientos"], 0, 37)}, "T3 R6: rendimientos débito Bancos / crédito 42100505 por el valor exacto")
chk(lados(DIA[6]) == {(C["banco"], 90000, 0), (C["por_cobrar_rappi"], 0, 90000)}, "T3 R6: abono Rappi con cuenta → crédito 13452501")
chk(not lados(DIA[2]) and not lados(DIA[4]), "T3: destino casilla (Rappi, QR) todavía no da filas propias (T6)")
chk(lados(DIA[3]) == {(C["puente"], 120000, 0), (C["banco"], 0, 120000)}, "T3: salida sin cuenta → puente 51959501 contra Bancos")
pe = {p["id"]: p for p in r["pendientes"]}
chk(set(pe) == {DIA[3]["clave"], DIA[5]["clave"]} and pe[DIA[3]["clave"]]["valor"] == 120000 and pe[DIA[3]["clave"]]["tipo"] == "extracto",
    "T3: cada línea a revisar deja un pendiente en el día")
chk(all(len(f["docs"]) == 1 and f["reporta"] for f in fx), "T3 S2: cada fila guarda docs=[clave] y grupo «Extracto»")
chk(any("extracto" in a and C["puente"] in a for a in r["avisos"]), "T3: aviso del día con las líneas que quedaron en el puente")
chk(A.construir("2026-09-25", [], {}, extracto=[])["filas"] == [] == A.construir("2026-09-25", [], {})["filas"], "T3: sin extracto el día sigue igual")
r = A.construir("2026-09-25", [], {}, extracto=[x for x in DIA if not x["destino"].startswith("casilla:")])   # las casillas salen con fórmula (probar_datos_ocr)
ws = load_workbook(io.BytesIO(E.libro_a_excel({"2026-09-25": r["filas"]}, datos={"2026-09-25": r["datos"]})))["MOVIMIENTOS SEPTIEMBRE"]
fl = [c for c in ws.iter_rows(min_row=9) if c[0].value is not None]
chk(len(fl) == len(r["filas"]) and sum(c[5].value or 0 for c in fl) == sum(c[6].value or 0 for c in fl) == r["debito"], "T3 R8: el Excel exportado trae las filas y cuadra débito = crédito")
eq = [c[4] for c in fl if str(c[4].value).startswith("=")]
chk(eq and all(c.data_type == "s" for c in eq), "T3 S5: una descripción del banco que empieza con «=» sale como texto")

# --- FIX-1: clasificar es idempotente
_c1 = X.clasificar([lin("IMPTO GOBIERNO 4X1000", 610), lin("COSA RARA", -5)], REGLAS)
chk(X.clasificar(_c1, REGLAS) == _c1 and _c1[0]["avisos"] == ["signo inesperado"], "FIX-1: clasificar(clasificar(L)) == clasificar(L), sin avisos duplicados")
_c2 = X.clasificar([dict(_c1[0], valor=-610)], REGLAS)
chk(_c2[0]["avisos"] == [], "FIX-1: si la regla ahora encaja, el aviso viejo se va")

# --- T6: casillas efectivas (R4, P1, ADR-012) ---
from parser_module.contable import leer_texto
from parser_module.contable.ejemplos import VENTA
QR2 = X.clasificar([lin("PAGO QR ANA", 30000), lin("PAGO QR LUIS", 34000), lin("IMPTO GOBIERNO 4X1000", -256)], REGLAS)
ef, dif = A.casillas_efectivas({}, QR2)
chk(ef.get("qr") == 64000 and dif == {}, f"T6: casilla qr vacía → la suma del extracto (64.000), sin diferencia ({ef}, {dif})")
ef, dif = A.casillas_efectivas({"qr": 70000, "nequi": "0"}, QR2)
chk(ef["qr"] == 70000 and dif == {"qr": 6000}, f"T6: casilla qr digitada 70.000 manda; dif = digitada − extracto = 6.000 ({ef}, {dif})")
ef, dif = A.casillas_efectivas({"qr": 64000}, QR2)
chk(dif == {}, "T6: digitada = extracto → sin diferencia")
bq = lambda r, medio: [f for f in r["filas"] if f["codigo"] == A.BANCO and f["debito"] and f["medio"] == medio]
r = A.construir("2026-09-25", [], {}, extracto=QR2)
chk([f["debito"] for f in bq(r, "QR")] == [64000] and r["diferencia"] == 0, f"T6: casilla QR vacía → 1 recaudo QR = extracto ({[f['debito'] for f in bq(r, 'QR')]})")
r = A.construir("2026-09-25", [], {"qr": 70000}, extracto=QR2)
chk([f["debito"] for f in bq(r, "QR")] == [70000], "ADR-012: recaudo contado dos veces (casilla digitada + líneas QR)")
chk(any("6.000" in a and "QR" in a for a in r["avisos"]), f"T6: aviso del día con la diferencia digitada − extracto ({r['avisos']})")
vt = leer_texto(VENTA)   # comanda 85531: 95.800 con tarjeta
TJ = X.clasificar([lin("ABONO NETO VISA", 95800)], REGLAS)
r = A.construir("2026-09-12", copy.deepcopy(vt), {}, extracto=TJ)
chk([f["debito"] for f in bq(r, "Tarjeta")] == [95800] and r["diferencia"] == 0, f"ADR-012: recaudo contado dos veces (comanda con tarjeta + abono neto) {[f['debito'] for f in bq(r, 'Tarjeta')]}")
chk(any(x["estado"] == "en extracto" and x["medio"] == "Tarjeta" for x in r["datos"]), "T6: la parte con tarjeta de la comanda queda «en extracto»")
r = A.construir("2026-09-12", copy.deepcopy(vt), {}, extracto=[])
chk([f["debito"] for f in bq(r, "Tarjeta")] == [95800], "T6: sin extracto el día sigue igual (la comanda con tarjeta entra sola)")

# --- T4: POST /api/contable/extracto (ADR-012, todo o nada) ---
import pathlib, time
import app as appmod
_t = pathlib.Path(tempfile.mkdtemp())
appmod.RUTA_LIBRO, appmod.RUTA_EXT_MEM, appmod.RUTA_SOPORTE = _t / "libro.json", _t / "extracto_memoria.json", _t / "soporte.db"
cli = appmod.app.test_client()
def sube(datos, nombre="e.xlsx"): return cli.post("/api/contable/extracto", data={"archivo": (io.BytesIO(datos), nombre)}, content_type="multipart/form-data")
def dia_(n): return _dt.datetime(2026, 9, n, 5, 0)
S1 = [(dia_(n), f"PAGO QR P{n}", "", 1000 * n) for n in range(1, 24)] + [(dia_(23), "IMPTO GOBIERNO 4X1000", "", -610), (dia_(23), "IMPTO GOBIERNO 4X1000", "", -610)]
S2 = S1 + [(dia_(n), f"PAGO QR P{n}", "", 1000 * n) for n in range(24, 31)]
r1 = sube(xlsx(S1)); j1 = r1.get_json()
chk(r1.status_code == 200 and (j1["nuevas"], j1["ya_estaban"]) == (25, 0), f"T4: importar 1–23 → 25 nuevas, 0 ya estaban ({j1})")
lib1 = appmod._leer_libro()
chk(len(lib1) == 23 and all(d["extracto"] for d in lib1.values()) and lib1["2026-09-23"]["debito"] == lib1["2026-09-23"]["credito"], "T4: crea los 23 días y los deja cuadrados")
chk(len(lib1["2026-09-23"]["extracto"]) == 3 and [x["ocurrencia"] for x in lib1["2026-09-23"]["extracto"] if x["valor"] == -610] == [1, 2], "T4: dos líneas idénticas del mismo día quedan ambas (ocurrencia 1 y 2)")
r2 = sube(xlsx(S2)); j2 = r2.get_json(); lib2 = appmod._leer_libro()
chk(r2.status_code == 200 and (j2["nuevas"], j2["ya_estaban"]) == (7, 25), f"T4: importar 1–30 → 7 nuevas, 25 ya estaban ({j2})")
chk(len(lib2) == 30 and sum(len(d["extracto"]) for d in lib2.values()) == 32, "T4: sin duplicar (32 líneas en 30 días)")
chk(j2["dias"] == [f"2026-09-{n}" for n in range(24, 31)], "T4: solo recalcula los días con líneas nuevas")
r3 = sube(xlsx(S2)); chk(r3.get_json()["nuevas"] == 0 and r3.get_json()["ya_estaban"] == 32, "T4: el mismo archivo otra vez: 0 nuevas")
mem = json.loads(appmod.RUTA_EXT_MEM.read_text(encoding="utf8"))
chk(len(mem["importaciones"]) == 3 and j1["imp"] in mem["importaciones"] and mem["importaciones"][j1["imp"]]["nuevas"] == 25 and not list(_t.glob("*.tmp")), "T4: importaciones[imp] en extracto_memoria.json (sin .tmp sobrantes)")
antes, mem_antes = appmod.RUTA_LIBRO.read_bytes(), appmod.RUTA_EXT_MEM.read_bytes()
malos = [b"no soy xlsx", xlsx(S1, hoja="Otra"), xlsx([(dia_(1), "A", "", 1), ("mala", "B", "", 2)])]
res = [sube(b) for b in malos]
chk(all(x.status_code == 400 and x.get_json()["error"] for x in res), "T4: archivo malo → 400 {error}")
chk(appmod.RUTA_LIBRO.read_bytes() == antes and appmod.RUTA_EXT_MEM.read_bytes() == mem_antes, "T4: archivo malo deja libro.json y la memoria byte a byte iguales")
chk(cli.post("/api/contable/extracto", data={}, content_type="multipart/form-data").status_code == 400, "T4: sin archivo → 400")
_rg = X.RUTA_REGLAS; X.RUTA_REGLAS = _t / "no_existe.json"
try: rr = sube(xlsx(S1))
finally: X.RUTA_REGLAS = _rg
chk(rr.status_code == 400 and appmod.RUTA_LIBRO.read_bytes() == antes, "T4: reglas rotas/ausentes → 400 sin escribir")

# --- T6: editar o recalcular un día con extracto conserva `extracto` y lo pasa a construir (hallado en T4) ---
qr_de = lambda d: [f["debito"] for f in d["filas"] if f["codigo"] == A.BANCO and f["medio"] == "QR"]
ext5 = appmod._leer_libro()["2026-09-05"]["extracto"]
chk(qr_de(appmod._leer_libro()["2026-09-05"]) == [5000], "T6: el import deja el recaudo QR del día 5 (casilla vacía = extracto)")
rc = cli.post("/api/contable/libro", json=dict(fecha="2026-09-05", documentos=[], banco={"qr": 5200}, cierre={}, reemplazar=True))
d5 = appmod._leer_libro()["2026-09-05"]
chk(rc.status_code == 200 and d5["extracto"] == ext5 and qr_de(d5) == [5200], f"T6: guardar el día otra vez conserva `extracto` y usa la casilla digitada ({rc.status_code}, {qr_de(d5)})")
rp = cli.post("/api/contable/asientos", json=dict(fecha="2026-09-06", documentos=[], banco={}))
chk(qr_de(rp.get_json()) == [6000], "T6: la vista previa del día usa el extracto guardado")
rs = cli.post("/api/soporte/compra", json=dict(fecha="2026-09-07", tercero="Proveedor X", descripcion="Hielo", valor=8000, medio="Efectivo"))
d7 = appmod._leer_libro()["2026-09-07"]
chk(rs.status_code == 200 and d7["extracto"] and qr_de(d7) == [7000] and d7["debito"] == d7["credito"], f"T6: añadir una compra manual recalcula con el extracto ({rs.status_code}, {qr_de(d7)})")
if XLSX.exists():
    _t2 = pathlib.Path(tempfile.mkdtemp()); appmod.RUTA_LIBRO, appmod.RUTA_EXT_MEM = _t2 / "libro.json", _t2 / "m.json"
    t0 = time.time(); rx = sube(XLSX.read_bytes()); dt = time.time() - t0
    chk(rx.status_code == 200 and rx.get_json()["nuevas"] == 513 and dt < 3, f"T4: el real (513 líneas) entra en {dt:.1f} s < 3 s")
    chk(sube(XLSX.read_bytes()).get_json()["ya_estaban"] == 513, "T4: el real otra vez: 513 ya estaban")

# --- T7: memoria por tercero (R5, ADR-014) ---
_M = {"ANA PRUEBA": "51050501"}
_t7 = X.clasificar([lin("TRANSF A ANA PRUEBA", -50000), lin("TRANSF A  ana   prueba 123", -1000), lin("TRANSFERENCIA CTA SUC VIRTUAL", -7000),
                    lin("TRANSF A OTRA PERSONA", -900), lin("PAGO PSE ANA PRUEBA", -300)], REGLAS, _M)
chk(_t7[0]["origen"] == "recordada" and _t7[0]["cuenta"] == "51050501" and _t7[0]["destino"].startswith("cuenta:") and _t7[0]["tercero"] == "ANA PRUEBA",
    "T7: «TRANSF A ANA PRUEBA» con memoria sale recordada en 51050501")
chk(_t7[1]["origen"] == "recordada", "T7: el tercero se normaliza (mayúsculas, espacios, número suelto)")
chk(_t7[2]["destino"] == "revisar" and _t7[2]["tercero"] == "" and _t7[2]["cuenta"] == "", "T7: línea opaca sigue en revisar")
chk(X.clasificar([lin("TRANSFERENCIA CTA SUC VIRTUAL", -7000)], REGLAS, {"": "51050501", "TRANSFERENCIA CTA SUC VIRTUAL": "51050501"})[0]["destino"] == "revisar", "T7: lo opaco no se recuerda aunque haya memoria")
chk(_t7[3]["destino"] == "revisar" and _t7[3]["tercero"] == "OTRA PERSONA", "T7: tercero sin memoria sigue en revisar, con el tercero puesto")
chk(_t7[4]["origen"] == "recordada", "T7: PSE saca el tercero")
chk(X.clasificar(_t7, REGLAS, _M) == _t7, "T7: idempotente con memoria")
chk(X.clasificar([lin("TRANSF A ANA PRUEBA", -1)], REGLAS, {"ANA PRUEBA": "mal"})[0]["destino"] == "revisar", "T7: memoria mal formada se ignora")
chk(X.clasificar([lin("IMPTO GOBIERNO 4X1000", -5)], REGLAS, {"": "51050501"})[0]["origen"] == "regla", "T7: una regla con cuenta no la pisa la memoria")

# --- T8: enlace salida ↔ factura (R4, ADR-015) ---
from parser_module.contable.documentos import _base as _bd
def fac8(i, fecha, valor, medio="Transferencia", tipo="factura"):
    return {**_bd(tipo, ""), "id": i, "fecha": fecha, "valor": valor, "medio": medio, "tercero": "Proveedor", "cuenta": "51359501"}
def sal8(valor=-120000, fecha="2026-09-25"): return dict(lin("PAGO PSE PROVEEDOR EJEMPLO SAS", valor), fecha=fecha)
_s = sal8()
_r0 = X.clasificar([_s], REGLAS, {}, [fac8("fa", "2026-09-25", 99000)])[0]
chk(_r0["destino"] == "revisar" and _r0["factura_id"] == "" and not _r0.get("sin_asiento"), "T8: 0 candidatas → sigue en revisar, sin enlace")
_r1 = X.clasificar([_s], REGLAS, {}, [fac8("fa", "2026-09-23", 120000)])[0]
chk(_r1["destino"] == "factura" and _r1["factura_id"] == "fa" and X.AV_CONFIRMAR in _r1["avisos"], "T8: 1 candidata → destino factura, factura_id y aviso «confirma»")
_r2 = X.clasificar([_s], REGLAS, {}, [fac8("fa", "2026-09-23", 120000), fac8("fb", "2026-09-26", 120000)])[0]
chk(_r2["destino"] == "revisar" and _r2["factura_id"] == "" and _r2.get("sin_asiento") is True and X.AV_CUAL in _r2["avisos"], "T8: 2 candidatas → revisar, sin enlace, sin_asiento y «¿cuál factura?»")
chk(X.clasificar([_s], REGLAS, {}, [fac8("fa", "2026-09-22", 120000)])[0]["factura_id"] == "fa", "T8: borde a 3 días (antes) → enlaza")
chk(X.clasificar([_s], REGLAS, {}, [fac8("fa", "2026-09-28", 120000)])[0]["factura_id"] == "fa", "T8: borde a 3 días (después) → enlaza")
chk(X.clasificar([_s], REGLAS, {}, [fac8("fa", "2026-09-21", 120000)])[0]["destino"] == "revisar", "T8: a 4 días → no enlaza")
chk(X.clasificar([_s], REGLAS, {}, [fac8("fa", "2026-09-25", 120000, medio="Efectivo")])[0]["destino"] == "revisar", "T8: una factura en efectivo nunca es candidata")
_d2 = X.clasificar([sal8(), sal8()], REGLAS, {}, [fac8("fa", "2026-09-24", 120000)])
chk([x["factura_id"] for x in _d2] == ["fa", ""] and _d2[1]["destino"] == "revisar", "T8: una factura no se enlaza a dos líneas")
_F8 = [fac8("fa", "2026-09-23", 120000), fac8("fb", "2026-09-24", 5000), fac8("fc", "2026-09-24", 5000)]
_c8 = X.clasificar([sal8(), sal8(-5000), lin("IMPTO GOBIERNO 4X1000", -610)], REGLAS, {}, _F8)
chk(X.clasificar(_c8, REGLAS, {}, _F8) == _c8, "T8: clasificar(clasificar(L, facturas), facturas) == clasificar(L, facturas)")
_sin = X.clasificar(_c8, REGLAS)[0]
chk(_sin["factura_id"] == "" and _sin["destino"] == "revisar" and X.AV_CONFIRMAR not in _sin["avisos"], "T8: sin la factura, el enlace y su aviso se van al reclasificar")
_F = fac8("fa", "2026-09-23", 120000)
_r8 = A.construir("2026-09-25", [_F], {}, extracto=X.clasificar([sal8()], REGLAS, {}, [_F]))
_cb = [f for f in _r8["filas"] if f["codigo"] == A.BANCO and f["credito"]]
chk(len(_cb) == 1 and _cb[0]["credito"] == 120000 and _r8["debito"] == _r8["credito"], "ADR-015: gasto pagado contado dos veces")
_s2 = dict(lin("TRANSF A ANA PRUEBA", -120000), fecha="2026-09-25")
_f2 = [fac8("fa", "2026-09-23", 120000), fac8("fb", "2026-09-26", 120000)]
_m2 = X.clasificar([_s2], REGLAS, {"ANA PRUEBA": "51050501"}, _f2)[0]
chk(_m2["destino"] == "revisar" and _m2.get("sin_asiento") is True and X.AV_CUAL in _m2["avisos"] and _m2["cuenta"] == "", "FIX-2: memoria + 2 facturas candidatas → sigue en revisar con «¿cuál factura?»")
_inv = X.clasificar([_s2, sal8(), lin("TRANSF A ANA PRUEBA", -5)], REGLAS, {"ANA PRUEBA": "51050501"}, _f2)
chk(all(x["destino"] == "revisar" for x in _inv if x.get("sin_asiento")) and any(x.get("sin_asiento") for x in _inv), "FIX-2: invariante, toda línea con sin_asiento tiene destino revisar")

# --- T9: revisión y asignación (R5, ADR-014/015) + sin_asiento + facturas= en la importación ---
_t9 = pathlib.Path(tempfile.mkdtemp()); appmod.RUTA_LIBRO, appmod.RUTA_EXT_MEM = _t9 / "libro.json", _t9 / "m.json"
_x2 = X.clasificar([sal8(-5000)], REGLAS, {}, [fac8("fa", "2026-09-23", 5000), fac8("fb", "2026-09-24", 5000)])
_r9 = A.construir("2026-09-25", [], {}, extracto=_x2)
chk(_x2[0].get("sin_asiento") and not _r9["filas"] and not _r9["pendientes"], "T9: 2 candidatas (sin_asiento) → ninguna fila ni puente 51959501 en el libro")
chk([f["codigo"] for f in A.construir("2026-09-25", [], {}, extracto=X.clasificar([sal8(-5000)], REGLAS))["filas"]].count("51959501") == 1, "T9: sin_asiento ausente → el puente sigue como antes")
_F9 = fac8("fa", "2026-09-23", 120000)
appmod.RUTA_LIBRO.write_text(json.dumps({"2026-09-23": dict(fecha="2026-09-23", documentos=[_F9], banco={}, cierre={})}), encoding="utf8")
_S9 = [(dia_(25), "PAGO PSE PROVEEDOR EJEMPLO SAS", "", -120000), (dia_(25), "TRANSF A ANA PRUEBA", "", -50000), (dia_(25), "TRANSF A TERCERO B", "", -7000)]
chk(sube(xlsx(_S9)).status_code == 200, "T9: importa")
_d9 = appmod._leer_libro()["2026-09-25"]; _e9 = {x["descripcion"]: x for x in _d9["extracto"]}
chk(_e9["PAGO PSE PROVEEDOR EJEMPLO SAS"]["factura_id"] == "fa" and _e9["PAGO PSE PROVEEDOR EJEMPLO SAS"]["destino"] == "factura", "T9: importar enlaza la salida a su única factura")
rv = cli.get("/api/contable/extracto/revision?desde=2026-09-01&hasta=2026-09-30").get_json()["lineas"]
chk(len(rv) == 3 and {x["fecha"] for x in rv} == {"2026-09-25"}, f"T9: revisión lista las 3 líneas ({len(rv)})")
chk(cli.get("/api/contable/extracto/revision?desde=mal").status_code == 400, "T9: revisión con fecha mala → 400")
k_lg, k_m, k_f = _e9["TRANSF A ANA PRUEBA"]["clave"], _e9["TRANSF A TERCERO B"]["clave"], _e9["PAGO PSE PROVEEDOR EJEMPLO SAS"]["clave"]
_u = lambda k, **b: cli.post(f"/api/contable/extracto/2026-09-25/{k}", json=b)
_rev = lambda: [x["clave"] for x in cli.get("/api/contable/extracto/revision").get_json()["lineas"]]
CT = next(c for c in A.CATALOGO if c.startswith("5105"))
chk(_u(k_lg, cuenta="99999999").status_code == 400 and _u(k_lg, cuenta=CT, factura_id="fa").status_code == 400, "T9: cuenta fuera del plan o dos opciones → 400")
chk(_u("0" * 16, cuenta=CT).status_code == 404 and _u(k_lg, factura_id="zzz").status_code == 400, "T9: línea o factura inexistente")
t0 = time.time(); ra = _u(k_lg, cuenta=CT, recordar=True); dt = time.time() - t0
da = ra.get_json()["dia"]
chk(ra.status_code == 200 and dt < 0.3, f"T9: asignar con recordar → 200 en {dt*1000:.0f} ms < 300")
chk(k_lg not in _rev(), "T9: asignar quita la línea de la revisión")
chk(any(f["codigo"] == CT and f["debito"] == 50000 for f in da["filas"]) and da["debito"] == da["credito"], "T9: la fila pasa de 51959501 a la cuenta elegida")
chk(json.loads(appmod.RUTA_EXT_MEM.read_text(encoding="utf8"))["memoria"].get("ANA PRUEBA") == CT and not list(_t9.glob("*.tmp")), "T9: recordar llena la memoria")
chk(any(x["clave"] == k_lg and x["asignada"] == {"cuenta": CT} for x in appmod._leer_libro()["2026-09-25"]["extracto"]), "T9: la asignación sobrevive a reclasificar")
chk(k_f in _rev(), "T9: el enlace único queda a confirmar en la revisión")
chk(_u(k_f, factura_id="ninguna").status_code == 200 and k_f in _rev(), "T9: «ninguna» rechaza el enlace: vuelve a revisar")
chk(_u(k_f, factura_id="fa").status_code == 200 and k_f not in _rev(), "T9: factura_id confirma el enlace y sale de la revisión")

# --- T10: diferencias por medio y «usar extracto» (R4) ---
_S10 = [(dia_(26), "PAGO QR CLIENTE UNO", "", 64000)]
chk(sube(xlsx(_S10)).status_code == 200, "T10: importa un abono QR")
_lib10 = appmod._leer_libro(); _lib10["2026-09-26"]["banco"] = {"qr": 70000}; appmod.RUTA_LIBRO.write_text(json.dumps(_lib10), encoding="utf8")
_k26 = _lib10["2026-09-26"]["extracto"][0]["clave"]
_df = cli.get("/api/contable/extracto/diferencias?desde=2026-09-01&hasta=2026-09-30").get_json()["diferencias"]
chk(len(_df) == 1 and _df[0]["fecha"] == "2026-09-26" and _df[0]["medio"] == "qr" and _df[0]["digitada"] == 70000 and _df[0]["extracto"] == 64000 and _df[0]["diferencia"] == 6000, f"T10: lista la diferencia QR 70.000 vs 64.000 ({_df})")
chk(cli.get("/api/contable/extracto/diferencias?desde=mal").status_code == 400, "T10: diferencias con fecha mala → 400")
chk(cli.post("/api/contable/extracto/2026-09-26/usar/zzz").status_code == 400 and cli.post("/api/contable/extracto/2026-09-20/usar/qr").status_code == 404, "T10: usar extracto con medio o día inexistente → 400/404")
_ru = cli.post("/api/contable/extracto/2026-09-26/usar/qr")
chk(_ru.status_code == 200 and not _ru.get_json()["dia"]["banco"].get("qr"), "T10: «usar extracto» borra la casilla digitada")
chk(cli.get("/api/contable/extracto/diferencias").get_json()["diferencias"] == [], "T10: la diferencia queda en 0 (no se lista)")
chk(bool(appmod._leer_libro()["2026-09-26"]["extracto"]), "T10: el día conserva el extracto")

# --- FIX-3: una factura no se enlaza a dos líneas de días distintos ---
_u3 = X.clasificar([sal8(-5000)], REGLAS, {}, [fac8("fa", "2026-09-23", 5000)], usadas=("fa",))[0]
chk(_u3["destino"] == "revisar" and _u3["factura_id"] == "", "FIX-3: clasificar con usadas iniciales excluye esa factura")
_F3 = fac8("F1", "2026-10-10", 50000)
def _nuevo3():
    d = pathlib.Path(tempfile.mkdtemp()); appmod.RUTA_LIBRO, appmod.RUTA_EXT_MEM = d / "libro.json", d / "m.json"
    appmod.RUTA_LIBRO.write_text(json.dumps({"2026-10-10": dict(fecha="2026-10-10", documentos=[_F3], banco={}, cierre={})}), encoding="utf8")
def _o3(n): return (_dt.datetime(2026, 10, n, 5, 0), "PAGO PSE PROVEEDOR EJEMPLO SAS", "", -50000)
def _enl3():
    l = appmod._leer_libro(); return {f: l[f]["extracto"][0] for f in ("2026-10-09", "2026-10-11")}, l
_nuevo3(); chk(sube(xlsx([_o3(9), _o3(11)])).status_code == 200, "FIX-3: importa juntas")
_e3, _l3 = _enl3()
chk(sorted(x["destino"] for x in _e3.values()) == ["factura", "revisar"] and sum(x["factura_id"] == "F1" for x in _e3.values()) == 1, f"FIX-3: juntas → solo una enlaza F1 ({[(x['destino'], x['factura_id']) for x in _e3.values()]})")
chk(any(f["codigo"] == "51959501" for d in _l3.values() for f in d.get("filas", [])), "FIX-3: la otra queda en revisar con puente")
_nuevo3(); sube(xlsx([_o3(9)])); sube(xlsx([_o3(9), _o3(11)]))
_e3, _l3 = _enl3()
chk(_e3["2026-10-09"]["factura_id"] == "F1" and _e3["2026-10-11"]["destino"] == "revisar" and _e3["2026-10-11"]["factura_id"] == "", "FIX-3: en dos importaciones → la segunda queda en revisar")
_k3 = _e3["2026-10-11"]["clave"]
chk(cli.post(f"/api/contable/extracto/2026-10-11/{_k3}", json=dict(factura_id="F1")).status_code == 400, "FIX-3: asignar a mano una factura ya enlazada en otra línea → 400")
chk(cli.post(f"/api/contable/extracto/2026-10-11/{_k3}", json=dict(cuenta=CT)).status_code == 200 and appmod._leer_libro()["2026-10-09"]["extracto"][0]["factura_id"] == "F1", "FIX-3: recalcular otro día no suelta el enlace")

print(f"\n{len(fallos)} fallos" if fallos else "\nTODO OK")
raise SystemExit(1 if fallos else 0)
