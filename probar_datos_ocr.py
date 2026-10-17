"""Prueba de la hoja DATOS OCR (R9, ADR-002): una fila por papel y medio de pago; ningún papel falta, ni los que van a puente."""
import copy, io, json, re, zipfile
from pathlib import Path
from openpyxl import load_workbook
from parser_module.contable import construir, leer_texto, libro_a_excel
from parser_module.contable.exportar import MESES
MESES_ = {m: i for i, m in enumerate(MESES, 1)}
from parser_module.contable.asientos import CFG, COLS_DATOS
from parser_module.contable.ejemplos import FOTO_PAPELES, GASTO, VENTA
ok = True
def chk(c, m):
    global ok; ok &= bool(c); print(("✓ " if c else "✗ ") + m)

PI, PG = CFG["puente_ingreso"], CFG["puente_gasto"]
docs = leer_texto(FOTO_PAPELES) + leer_texto(VENTA)
v = docs[-1]; f = next(d for d in docs if d["tipo"] == "factura")
docs += [dict(v, id="sinmedio", numero="85600", efectivo=0, tarjeta=0, transf=0, credito=0, avisos=[]), dict(f, id="sinvalor", numero="POS2", valor=0, avisos=[])]
docs += [dict(v, id="ilegible", numero="85601", consumo=0, propina=0, efectivo=0, tarjeta=0, transf=0, credito=0, avisos=[])]
docs += leer_texto(GASTO.format(n=300, v="5,000", d="algo raro"))   # gasto de caja sin cuenta
r = construir("2026-09-12", docs, {"tarjetas": 146500})
D = r["datos"]
chk(set(D[0]) == set(COLS_DATOS), f"columnas de ADR-002: {COLS_DATOS}")
ids = [x["id"] for x in D if x["id"]]
chk(set(ids) == {d["id"] for d in r["documentos"]}, f"cada papel del día tiene su fila: {len(set(ids))} de {len(r['documentos'])}")
p = {x["id"]: x for x in D}
v_ = [x for x in D if x["id"] == v["id"]]
chk([(x["medio"], x["valor"], x["cuenta"], x["estado"]) for x in v_] == [("Efectivo", 100000, "11050501", "ok"), ("Tarjeta", 95800, "11200501", "en extracto")],
    f"venta mixta → 2 filas (efectivo y tarjeta; la tarjeta la cubre el extracto): {[(x['medio'], x['valor'], x['estado']) for x in v_]}")
chk(p["sinmedio"]["cuenta"] == PI and p["sinmedio"]["medio"] == "(sin medio)" and p["sinmedio"]["aviso"], f"venta sin medio → fila en {PI} con aviso")
g = next(x for x in D if x["numero"] == "300")
chk(g["cuenta"] == PG and g["estado"] == "ok" and g["aviso"], f"gasto sin cuenta → fila en {PG} con aviso")
chk(p["ilegible"]["estado"] == "pendiente" and p["ilegible"]["aviso"], "venta sin ninguna cifra leída → fila «pendiente» (no se pierde de vista)")
chk(p["sinvalor"]["estado"] == "pendiente" and p["sinvalor"]["valor"] == 0, "factura sin valor → estado «pendiente»")
dup = [x for x in D if x["estado"] == "no cuenta"]
chk(len(dup) == 3 and all("duplicado" in x["aviso"] for x in dup), f"los 3 manuscritos duplicados se ven como «no cuenta»: {len(dup)}")
ext = [x for x in D if x["tipo"] == "extracto"]
chk([(x["valor"], x["medio"], x["bloque"]) for x in ext] == [(146500, "Tarjeta", "extracto")], "el extracto bancario también es una fila")
# los importes que suman («ok») dan lo mismo que el libro, por bloque
caja = sum(x["valor"] for x in D if x["bloque"] == "caja" and x["estado"] == "ok")
chk(caja == next(x["credito"] for x in r["filas"] if x["tercero"] == "Cuantías menores" and x["credito"]), f"caja menor en DATOS OCR = crédito a Efectivo del libro ({caja:,})")

# Excel: DATOS OCR va primero, con una fila por dato y sin macros
x = libro_a_excel({"2026-09-12": r["filas"]}, datos={"2026-09-12": D})
wb = load_workbook(io.BytesIO(x))
ws = wb.worksheets[0]
filas = [f_ for f_ in ws.iter_rows(min_row=2, values_only=True) if any(f_)]
chk(ws.title == "DATOS OCR" and len(filas) == len(D), f"hoja DATOS OCR primera, {len(filas)} filas = {len(D)} datos")
chk(not any("vbaProject" in n for n in zipfile.ZipFile(io.BytesIO(x)).namelist()), "ADR-002: el libro no trae macros")
chk("DATOS OCR" not in load_workbook(io.BytesIO(libro_a_excel({"2026-09-12": r["filas"]}))).sheetnames, "sin datos no se agrega la hoja (compatibilidad)")


# T6 · MOVIMIENTOS con fórmulas. openpyxl no calcula y aquí no hay Excel: un evaluador mínimo (refs, SUMIFS, MIN, SUM, + y −) hace de Excel.
TOK = re.compile(r"\s*(?:(?P<num>\d+(?:\.\d+)?)|(?P<str>\"(?:[^\"]|\"\")*\")|(?P<ref>(?:'[^']+'!)?\$?[A-Z]+\$?\d*(?::\$?[A-Z]+\$?\d*)?)(?P<fn>\()?|(?P<op>[-+(),=]))")
def evaluar(wb, hoja, celda, memo):
    if (hoja, celda) in memo: return memo[hoja, celda]
    v = wb[hoja][celda].value
    if isinstance(v, str) and v.startswith("="):
        toks = [m for m in TOK.finditer(v[1:]) if m.group()]; i = 0
        def rango(t):
            h, _, r_ = t.rpartition("!"); h = h.strip("'") or hoja; a, _, b = r_.replace("$", "").partition(":")
            ws = wb[h]; ca, cb = re.sub(r"\d", "", a), re.sub(r"\d", "", b)
            fa, fb = (int(re.sub(r"\D", "", a)), int(re.sub(r"\D", "", b))) if re.search(r"\d", a) else (1, ws.max_row)
            return [[(h, f"{c}{k}") for k in range(fa, fb + 1)] for c in sorted({ca, cb})][0]
        def igual(x, crit):
            if isinstance(crit, str):
                neg = crit.startswith("<>"); c = crit[2:] if neg else crit.removeprefix("=")
                c = re.sub(r"~(.)", r"\1", c); s = "" if x is None else str(x)
                e = s.lower() == c.lower() or (s.replace(".0", "") == c)
                return e != neg
            return x == crit
        def atomo():
            nonlocal i
            t = toks[i]; i += 1
            if t["op"] == "(": x = expr(); i += 1; return x
            if t["num"]: return float(t["num"])
            if t["str"]: return t["str"][1:-1].replace('""', '"')
            if t["fn"]:
                args = []
                while True:
                    if toks[i]["ref"] and ":" in toks[i]["ref"] and toks[i + 1]["op"] in (",", ")"): args.append(rango(toks[i]["ref"])); i += 1
                    else: args.append(expr())
                    i += 1
                    if toks[i - 1]["op"] == ")": break
                fn = t["ref"].upper()
                if fn == "MIN": return min(args)
                if fn == "IF": return args[1] if args[0] else args[2]
                if fn == "SUM": return sum(evaluar(wb, h, c, memo) or 0 for h, c in args[0])
                if fn == "SUMIFS":
                    tot = 0
                    for k, (h, c) in enumerate(args[0]):
                        if k == 0: continue   # encabezado
                        if all(igual(wb[args[n][k][0]][args[n][k][1]].value, args[n + 1]) for n in range(1, len(args), 2)): tot += wb[h][c].value or 0
                    return tot
                raise ValueError(fn)
            h, _, c = t["ref"].rpartition("!")
            return evaluar(wb, h.strip("'") or hoja, c.replace("$", ""), memo)
        def suma():
            nonlocal i
            x = atomo()
            while i < len(toks) and toks[i]["op"] in ("+", "-"):
                o = toks[i]["op"]; i += 1; y = atomo(); x = x + y if o == "+" else x - y
            return x
        def expr():   # comparación «=» (para IF), sin distinguir mayúsculas como Excel
            nonlocal i
            x = suma()
            if i < len(toks) and toks[i]["op"] == "=": i += 1; y = suma(); return igual(x, y)
            return x
        v = expr()
    memo[hoja, celda] = v; return v

def movimientos(wb):
    ws = next(w for w in wb.worksheets if w.title.startswith("MOVIMIENTOS")); memo = {}
    return ws, [(r, evaluar(wb, ws.title, f"F{r}", memo), evaluar(wb, ws.title, f"G{r}", memo)) for r in range(9, ws.max_row + 1) if ws[f"B{r}"].value]

ws, mov = movimientos(wb)
imp = [ws[f"{'G' if f['fx'][0] == 'credito' else 'F'}{k}"].value for k, f in enumerate(r["filas"], 9)]
chk(all(isinstance(x, str) and x.startswith("=") for x in imp), f"ADR-002: cada importe de MOVIMIENTOS es una fórmula ({len(imp)} filas)")
chk(any("'DATOS OCR'!" in x and "SUMIFS" in x for x in imp) and any(re.fullmatch(r"=IF\('DATOS OCR'!J(\d+)=\"ok\",'DATOS OCR'!G\1,0\)", x) for x in imp), "hay SUMIFS por fecha/estado/cuenta y referencias a DATOS OCR que miran el estado")
chk([(int(d), int(c)) for _, d, c in mov] == [(f["debito"], f["credito"]) for f in r["filas"]], "evaluadas, las fórmulas dan lo mismo que construir()")
# corregir a mano en DATOS OCR: el efectivo de la venta mixta pasa de 100.000 a 130.000
fe = next(k for k, x in enumerate(D, 2) if x["id"] == v["id"] and x["medio"] == "Efectivo")
wb["DATOS OCR"][f"G{fe}"] = 130000
_, mov2 = movimientos(wb)
cambio = {r_: (d2 - d1, c2 - c1) for (r_, d1, c1), (_, d2, c2) in zip(mov, mov2) if (d1, c1) != (d2, c2)}
fil = {k: f for k, f in enumerate(r["filas"], 9)}
chk(sorted((fil[k]["codigo"], dc) for k, dc in cambio.items()) == [("11050501", (30000, 0)), ("41401501", (0, 30000))],
    f"cambiar un valor en DATOS OCR mueve Efectivo y la contrapartida de ingresos: {[(fil[k]['codigo'], dc) for k, dc in cambio.items()]}")
chk(evaluar(wb, ws.title, "F7", {}) == evaluar(wb, ws.title, "G7", {}), "y el mes sigue cuadrando (total débito = total crédito)")
wb["DATOS OCR"][f"J{fe}"] = "no cuenta"   # marcar el papel como «no cuenta» lo saca del libro
_, mov3 = movimientos(wb)
chk(sum(d for _, d, _ in mov3) == sum(f["debito"] for f in r["filas"]) - 100000, "cambiar el estado a «no cuenta» saca ese valor del libro")
# FIX-2: las filas «dato» (facturas, extracto, Rappi) también respetan el estado
kf = next(k for k, f_ in enumerate(r["filas"], 9) if f_.get("fx", [None, [None]])[1][0] == "dato" and f_.get("docs") == [f["id"]])
ff = next(k for k, x_ in enumerate(D, 2) if x_["id"] == f["id"] and x_["valor"])
wb["DATOS OCR"][f"J{ff}"] = "no cuenta"
_, mov4 = movimientos(wb)
chk(dict((q, d) for q, d, _ in mov4)[kf] == 0, f"una factura en «no cuenta» → 0 en MOVIMIENTOS (fila {kf}: {dict((q, d) for q, d, _ in mov4)[kf]:,})")
chk(evaluar(wb, ws.title, "F7", {}) == evaluar(wb, ws.title, "G7", {}), "y el mes sigue cuadrando sin esa factura")
# FIX-3: caja menor con un gasto sin cuenta (A) y otro ya en la cuenta puente (B) → una sola fila, un solo SUMIFS
a = leer_texto(GASTO.format(n=301, v="5,000", d="algo raro"))[0]
b = dict(leer_texto(GASTO.format(n=302, v="7,000", d="algo raro"))[0], cuenta=PG)
r3 = construir("2026-09-13", [a, b])
pg = [f_ for f_ in r3["filas"] if f_["codigo"] == PG and f_["tercero"] == "Cuantías menores"]
chk(len(pg) == 1 and pg[0]["debito"] == 12000, f"gasto sin cuenta + gasto en {PG} → 1 fila de 12.000: {[f_['debito'] for f_ in pg]}")
w3 = load_workbook(io.BytesIO(libro_a_excel({"2026-09-13": r3["filas"]}, datos={"2026-09-13": r3["datos"]})))
s3, m3 = movimientos(w3)
chk(evaluar(w3, s3.title, "F7", {}) == evaluar(w3, s3.title, "G7", {}) and [(int(d), int(c)) for _, d, c in m3] == [(f_["debito"], f_["credito"]) for f_ in r3["filas"]],
    "y en Excel débito = crédito (no se suma doble)")
# DEBT-1: construir() no clasifica por su cuenta; sus filas salen de DATOS OCR (cambiar una fila allí cambia el libro)
import parser_module.contable.asientos as A
orig = A.datos_ocr
def otra_cuenta(*a_, **k_):
    ds = orig(*a_, **k_); next(x for x in ds if x["bloque"] == "caja")["cuenta"] = "52959501"; return ds
A.datos_ocr = otra_cuenta
try: r4 = construir("2026-09-13", [copy.deepcopy(a)])
finally: A.datos_ocr = orig
chk([f_["codigo"] for f_ in r4["filas"] if f_["debito"]] == ["52959501"], "DEBT-1: la cuenta de la fila de caja sale de DATOS OCR")
chk(construir("2026-09-13", [copy.deepcopy(a)])["filas"][0]["codigo"] == PG, "y sin el cambio vuelve a la cuenta puente")
av = load_workbook(io.BytesIO(x))["AVISOS"]
chk(any("grupo nuevo" in (c.value or "") for c in av["A"]), "AVISOS explica que un grupo nuevo no agrega fila en MOVIMIENTOS")

# FIX-12 · texto libre que empieza por = + - @ queda como texto (CWE-1236), las fórmulas propias siguen siendo fórmulas
INY = '=HYPERLINK("x")'
r12 = construir("2026-09-14", [dict(f, id="iny", numero="POS9", valor=12000, tercero=INY, detalle="@SUM(1)", avisos=[])])
w12 = load_workbook(io.BytesIO(libro_a_excel({"2026-09-14": r12["filas"]}, datos={"2026-09-14": r12["datos"]})))
celdas = [c for w in w12.worksheets for fila_ in w.iter_rows() for c in fila_ if isinstance(c.value, str) and ("HYPERLINK" in c.value or "@SUM" in c.value)]
chk(celdas and all(c.data_type == "s" and c.quotePrefix for c in celdas) and {c.parent.title for c in celdas} >= {"DATOS OCR", "MOVIMIENTOS SEPTIEMBRE"},
    f"FIX-12: tercero/detalle «{INY}» quedan como texto en DATOS OCR y MOVIMIENTOS: {[(c.parent.title, c.coordinate, c.data_type) for c in celdas]}")
chk(any(c.data_type == "f" for c in w12["MOVIMIENTOS SEPTIEMBRE"]["F"] + w12["MOVIMIENTOS SEPTIEMBRE"]["G"]), "FIX-12: los importes de MOVIMIENTOS siguen siendo fórmulas")

# fitness ADR-002 con los días guardados (si hay libro.json): cada día evaluado = construir()
LIB = Path(__file__).parent / "datos" / "libro.json"
if LIB.exists():
    lib = json.loads(LIB.read_text(encoding="utf-8")); rs = {k: construir(k, copy.deepcopy(d["documentos"]), d.get("banco"), None, d.get("cierre")) for k, d in lib.items()}
    wb = load_workbook(io.BytesIO(libro_a_excel({k: q["filas"] for k, q in rs.items()}, datos={k: q["datos"] for k, q in rs.items()})))
    malos, n = [], 0
    for w in [w for w in wb.worksheets if w.title.startswith("MOVIMIENTOS")]:
        memo, m = {}, MESES_[w.title.split()[1]]; esp = [(f["debito"], f["credito"]) for k in sorted(rs) if int(k[5:7]) == m for f in rs[k]["filas"]]
        got = [(int(evaluar(wb, w.title, f"F{q}", memo)), int(evaluar(wb, w.title, f"G{q}", memo))) for q in range(9, w.max_row + 1) if w[f"B{q}"].value]
        n += len(got); malos += [q for q, (a, b) in enumerate(zip(got, esp)) if a != b] + ([-1] if len(got) != len(esp) else [])
    chk(not malos, f"libro.json: {len(rs)} días, {n} asientos con fórmula = construir() (distintos: {len(malos)})")
# T18 · ADR-004: archivo crudo .json (formato, version, sha256; solo lo leído, sin lo derivado), filtrado por rango
from parser_module.contable.exportar import crudo, huella
lib18 = {"2026-09-13": dict(fecha="2026-09-13", documentos=r3["documentos"], banco={"x": 1}, cierre={"y": [2]}, cruces=[], filas=r3["filas"], debito=1, credito=1, guardado="2026-09-14T08:00:00"),
         "2026-09-14": dict(fecha="2026-09-14", documentos=r12["documentos"], banco={}, cierre={}, filas=r12["filas"], guardado="2026-09-15T08:00:00"),
         "2026-09-20": dict(fecha="2026-09-20", documentos=[], banco={}, cierre={}, filas=[], guardado="")}
j18 = json.loads(crudo(lib18, "2026-09-13", "2026-09-14").decode("utf-8"))
chk(j18["formato"] == "ingresos-crudo" and j18["version"] == 1 and (j18["desde"], j18["hasta"]) == ("2026-09-13", "2026-09-14") and j18["exportado"],
    f"T18: cabecera formato/version/desde/hasta/exportado: {[j18.get(k) for k in ('formato', 'version', 'desde', 'hasta')]}")
chk([d["fecha"] for d in j18["dias"]] == ["2026-09-13", "2026-09-14"], f"T18: solo los días del rango, en orden: {[d['fecha'] for d in j18['dias']]}")
chk(all(set(d) == {"fecha", "documentos", "banco", "cierre", "guardado"} for d in j18["dias"]), "T18: cada día lleva solo lo leído (sin filas/cruces/débito, que se recalculan)")
chk(all(d == {k: lib18[d["fecha"]][k] for k in d} for d in j18["dias"]), "ADR-004: la ida y vuelta perdió datos (documentos/banco/cierre/guardado)")
chk(j18["sha256"] == huella(j18["dias"]) and huella(j18["dias"][:1]) != j18["sha256"], "T18: sha256 sobre los días coincide y cambia si falta un día")
chk(json.loads(crudo(lib18, "", "").decode("utf-8"))["dias"].__len__() == 3, "T18: sin rango exporta todos los días")
if LIB.exists():
    jl = json.loads(crudo(lib, "", ""))
    chk(len(jl["dias"]) == len(lib) and all(d["documentos"] == lib[d["fecha"]]["documentos"] for d in jl["dias"]) and jl["sha256"] == huella(jl["dias"]),
        f"T18: libro.json real ({len(lib)} días) exporta y vuelve a leerse igual")
import tempfile, app as web
T18 = Path(tempfile.mkdtemp()); web.RUTA_LIBRO = T18 / "libro.json"; web.RUTA_LIBRO.write_text(json.dumps(lib18), encoding="utf8")
cl18 = web.app.test_client(); rq = cl18.get("/api/contable/crudo?desde=2026-09-14&hasta=2026-09-30")
jr = json.loads(rq.data) if rq.status_code == 200 else {}
chk(rq.status_code == 200 and "ingresos_crudo_2026-09-14_2026-09-30.json" in rq.headers.get("Content-Disposition", "")
    and [d["fecha"] for d in jr.get("dias", [])] == ["2026-09-14", "2026-09-20"] and jr["sha256"] == huella(jr["dias"]), f"T18: GET /api/contable/crudo descarga el rango: {rq.status_code}")
chk(cl18.get("/api/contable/crudo?desde=2027-01-01").status_code == 404 and cl18.get("/api/contable/crudo?desde=1/9/26").status_code == 400, "T18: rango vacío → 404, fecha mal → 400")
chk(cl18.get("/api/contable/crudo", headers={"Host": "evil.example.com"}).status_code == 403, "T18: Host ajeno → 403 (FIX-10)")
# T19 · ADR-004: importar el archivo crudo (valida archivo y días; nuevo entra, igual se omite, distinto = conflicto, R7 bloquea, R10 informa)
from dataclasses import asdict
from datetime import date as _date
from parser_module.contable import soporte as _sop
from parser_module.contable.exportar import leer_crudo, CrudoInvalido
def _arch(j, **cambios):
    j = {**copy.deepcopy(j), **cambios}
    if "sha256" not in cambios: j["sha256"] = huella(j["dias"])
    return json.dumps(j, ensure_ascii=False).encode("utf-8")
def _rechaza(data):
    try: leer_crudo(data); return ""
    except CrudoInvalido as e: return str(e)
lib19 = {f: dict(fecha=f, documentos=r["documentos"], banco={}, cierre={}, cruces=r["cruces"], filas=r["filas"], pendientes=r["pendientes"], debito=r["debito"],
                 credito=r["credito"], diferencia=r["diferencia"], guardado="2026-09-15T08:00:00") for f, r in (("2026-09-13", r3), ("2026-09-14", r12))}
a19 = crudo(lib19); j19 = json.loads(a19)
d19, m19 = leer_crudo(a19)
chk(not m19 and [d["fecha"] for d in d19] == ["2026-09-13", "2026-09-14"] and all(d == {k: lib19[d["fecha"]][k] for k in d} for d in d19), "ADR-004: la ida y vuelta perdió datos (leer_crudo)")
msg = _rechaza(_arch(j19, version=2))
chk("versión 2" in msg and "versión 1" in msg, f"T19: otra versión se rechaza con mensaje claro: {msg!r}")
chk(all(_rechaza(x) for x in (_arch(j19, sha256="0" * 64), _arch(j19, formato="otro"), b"{no es json", a19[: len(a19) // 2], b"\xff\xfe")),
    "ADR-004: archivo ajeno aceptado (sha256 distinta, otro formato, JSON roto, cortado)")
malo = copy.deepcopy(j19["dias"][0])
casos = [dict(malo, fecha="2026-02-30"), dict(malo, fecha="2026-09-01", documentos=[dict(malo["documentos"][0], tipo="pickle")]),
         dict(malo, fecha="2026-09-02", documentos=[dict(malo["documentos"][0], valor=10**11)]), dict(malo, fecha="2026-09-03", documentos=[dict(malo["documentos"][0], texto="x" * 5001)]),
         dict(malo, fecha="2026-09-04", documentos=[{"tipo": "factura"}]), dict(malo, fecha="2026-09-05", banco=[1]), dict(malo, fecha="2026-09-06", documentos=["x"] * 2001),
         dict(malo, fecha="2026-09-13")]
d19b, m19b = leer_crudo(_arch(j19, dias=j19["dias"] + casos))
chk([d["fecha"] for d in d19b] == ["2026-09-13", "2026-09-14"] and len(m19b) == len(casos) and all(x["motivo"] for x in m19b),
    f"T19: días malos (fecha, tipo, > 10^10, texto largo, sin id, banco, >2000, repetido) salen con motivo y los buenos quedan: {[x['motivo'][:25] for x in m19b]}")
T19 = Path(tempfile.mkdtemp()); web.RUTA_LIBRO, web.RUTA_CONT, web.RUTA_SOPORTE = T19 / "libro.json", T19 / "contable.json", T19 / "soporte.db"
imp = lambda data, reemplazar="": cl18.post("/api/contable/crudo", data={"archivo": (io.BytesIO(data), "c.json"), "reemplazar": reemplazar}, content_type="multipart/form-data")
r = imp(_arch(j19, version=2))
chk(r.status_code == 400 and "versión" in r.get_json()["error"] and not web.RUTA_LIBRO.exists(), f"T19: POST con otra versión → 400 sin escribir: {r.status_code}")
r = imp(_arch(j19, dias=j19["dias"] + casos[:2])); ji = r.get_json(); li = web._leer_libro()
chk(r.status_code == 200 and ji["nuevos"] == ["2026-09-13", "2026-09-14"] and len(ji["invalidos"]) == 2 and sorted(li) == ["2026-09-13", "2026-09-14"],
    f"T19: libro vacío → entran los días buenos, los malos van al informe: {r.status_code} {ji and {k: len(v) for k, v in ji.items() if isinstance(v, list)}}")
chk(len(li) == 2 and all(li[f][k] == lib19[f][k] for f in li for k in ("documentos", "banco", "cierre", "filas", "pendientes", "debito", "credito", "guardado")),
    "ADR-004: la ida y vuelta perdió datos (POST: documentos, filas y totales iguales)")
hoy = _date(2026, 9, 20)
chk([asdict(g) for g in _sop.semanas(li, None, None, hoy)] == [asdict(g) for g in _sop.semanas(lib19, None, None, hoy)], "T19: export → import da las mismas semanas de documento soporte")
antes = web.RUTA_LIBRO.read_bytes(); ji = imp(a19).get_json()
chk(ji["iguales"] == ["2026-09-13", "2026-09-14"] and not ji["nuevos"] and web.RUTA_LIBRO.read_bytes() == antes, "T19: importar otra vez el mismo archivo → iguales, libro sin tocar")
otro = copy.deepcopy(j19); otro["dias"][1]["documentos"][0]["valor"] = 99000
ji = imp(_arch(otro)).get_json()
chk([c["fecha"] for c in ji["conflictos"]] == ["2026-09-14"] and web._leer_libro()["2026-09-14"]["documentos"][0]["valor"] == 12000, "T19: día distinto → conflicto, no se toca")
ji = imp(_arch(otro), "2026-09-14").get_json()
chk(ji["reemplazados"] == ["2026-09-14"] and web._leer_libro()["2026-09-14"]["documentos"][0]["valor"] == 99000, "T19: marcado para reemplazar → se reemplaza")
_b = web._bloqueos; web._bloqueos = lambda f, d: ["CTG-1 (transmitido): la compra cambia"] if f == "2026-09-14" else []
ji = imp(a19, "2026-09-14").get_json(); web._bloqueos = _b
chk([x["fecha"] for x in ji["bloqueados"]] == ["2026-09-14"] and not ji["reemplazados"] and web._leer_libro()["2026-09-14"]["documentos"][0]["valor"] == 99000,
    "T19: R7 — un día con compras de un DS transmitido nunca se reemplaza")
chk(cl18.post("/api/contable/crudo", headers={"Host": "evil.example.com"}).status_code == 403 and imp(b"").status_code == 400 and cl18.post("/api/contable/crudo").status_code == 400,
    "T19: Host ajeno → 403; archivo vacío o ausente → 400")
# FIX-13 · un cierre con faltante (faltante_impreso negativo, documentos.py) va y vuelve igual por crudo → leer_crudo → POST
cie13 = dict(id="cierre-13", tipo="cierre", archivo="cierre.jpg", datos=dict(efectivo=150000, faltante_impreso=-3500), avisos=[], valor=-3500, contar=False)
lib13 = {"2026-09-21": dict(fecha="2026-09-21", documentos=[cie13], banco={}, cierre={"faltante": -3500}, guardado="2026-09-22T08:00:00")}
a13 = crudo(lib13); d13, m13 = leer_crudo(a13)
T13 = Path(tempfile.mkdtemp()); web.RUTA_LIBRO = T13 / "libro.json"; ji13 = imp(a13).get_json(); l13 = web._leer_libro()
chk(not m13 and d13[0]["documentos"] == [cie13] and ji13["nuevos"] == ["2026-09-21"] and l13["2026-09-21"]["documentos"] == [cie13]
    and l13["2026-09-21"]["cierre"] == {"faltante": -3500}, f"FIX-13: un día con faltante (negativo) no entra al importar: {m13} {ji13}")
if LIB.exists():
    T19b = Path(tempfile.mkdtemp()); web.RUTA_LIBRO, web.RUTA_CONT = T19b / "libro.json", LIB.parent / "contable.json"
    ji = imp(crudo(lib)).get_json(); li, cfg = web._leer_libro(), web._cont_cfg()
    esp = {f: construir(f, copy.deepcopy(d["documentos"]), d.get("banco", {}), cfg, d.get("cierre")) for f, d in lib.items()}
    malos = [f for f in lib if f not in li or li[f]["documentos"] != lib[f]["documentos"] or li[f]["filas"] != esp[f]["filas"]]
    chk(not ji["invalidos"] and len(ji["nuevos"]) == len(lib) and not malos, f"T19: libro.json real ({len(lib)} días) export → import en vacío: mismos documentos y filas (distintos: {malos[:3]})")
    chk([asdict(g) for g in _sop.semanas(li, None, None, hoy)] == [asdict(g) for g in _sop.semanas(lib, None, None, hoy)], "T19: libro real → mismas semanas")
print("\n" + ("TODO OK" if ok else "HAY FALLOS"))
