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
chk(len(fx) == 2 * 5 and len(r["filas"]) == len(fx), f"T3: 5 líneas cuenta/revisar → 10 filas «Extracto» ({len(fx)})")
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
if XLSX.exists():
    _t2 = pathlib.Path(tempfile.mkdtemp()); appmod.RUTA_LIBRO, appmod.RUTA_EXT_MEM = _t2 / "libro.json", _t2 / "m.json"
    t0 = time.time(); rx = sube(XLSX.read_bytes()); dt = time.time() - t0
    chk(rx.status_code == 200 and rx.get_json()["nuevas"] == 513 and dt < 3, f"T4: el real (513 líneas) entra en {dt:.1f} s < 3 s")
    chk(sube(XLSX.read_bytes()).get_json()["ya_estaban"] == 513, "T4: el real otra vez: 513 ya estaban")

print(f"\n{len(fallos)} fallos" if fallos else "\nTODO OK")
raise SystemExit(1 if fallos else 0)
