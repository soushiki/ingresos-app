"""Prueba del minado del manual (T2, ADR-020/N5): léxico ≥ 2 veces y ≥ 80 %, proveedores, vecinos con fuente, --meses, y que el modelo no lleve
valores, fechas ni nombres de personas. Con datos sintéticos; si el Excel real está, también se prueba el modelo de producción."""
import json, re, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "herramientas"))
import minar_manual as M

ok = True
def chk(c, m):
    global ok; ok &= bool(c); print(("✓ " if c else "✗ ") + m)

def f(hoja, fila, cod, ter, desc, deb=1000.0, rep="Caja"):
    return dict(hoja=hoja, fila=fila, mes={"JUNIO": "2026-06", "JULIO": "2026-07", "AGOSTO": "2026-08", "SEPTIEMBRE": "2026-09"}[hoja.split()[1]],
                codigo=cod, tercero=ter, desc=desc, deb=deb, cre=0.0, reporta=rep)
J, L, A, S = "MOVIMIENTOS JUNIO", "MOVIMIENTOS JULIO", "MOVIMIENTOS AGOSTO", "MOVIMIENTOS SEPTIEMBRE"
filas = [
    f(J, 10, "28150501", "Rappi", "Pago de domicilios"), f(L, 631, "28150501", "Cliente", "Domicilios fin de semana"), f(A, 20, "28150501", "", "Pago domicilios 12345"),
    f(J, 11, "51353001", "Afinia", "Pago recibo de la luz"), f(L, 12, "51353001", "Afinia", "Pago recibo luz"),
    f(L, 13, "14050501", "Plaza", "Compra de carne"), f(A, 14, "51952501", "Plaza", "Compra de carne"),          # carne 1 de 2: 50 % → no entra
    f(S, 15, "28150501", "Rappi", "Pago domicilios sept"),
    f(J, 1, "51050601", "Luisa Perez", "Pago quincena Luisa", rep="Marta"), f(L, 2, "51050601", "Luisa Perez", "Quincena Luisa"),
    f(J, 3, "31050501", "Pedro Gomez", "Aporte inicial", rep="Marta"),
    f(J, 4, "11200501", "Consumidor Final", "Recaudos a través de QR"), f(L, 5, "11200501", "Consumidor Final", "Recaudos a través de QR"),
]
m = M.minar(filas)
chk(m["lexico"].get("domicilios", {}).get("cuenta") == "28150501" and m["lexico"]["domicilios"]["n"] == 4, "léxico: «domicilios» → 28150501 (4 de 4)")
chk("carne" not in m["lexico"], "léxico: «carne» (50 %) no entra")
chk("luz" in m["lexico"] and m["lexico"]["luz"]["de"] == 2, "léxico: se necesitan ≥ 2 veces («luz» 2 de 2)")
chk("sept" not in m["lexico"] and "recaudos" not in m["lexico"], "léxico: palabras vacías y ventas fuera")
chk(m["proveedores"].get("afinia", {}).get("cuenta") == "51353001" and m["proveedores"]["rappi"]["n"] == 2, "proveedores: afinia y rappi con su cuenta")
chk("consumidor final" not in m["proveedores"] and "luisa perez" not in m["proveedores"] and "pedro gomez" not in m["proveedores"], "proveedores: sin genéricos ni personas")
chk(any(v["fuente"] == "julio fila 631" and v["cuenta"] == "28150501" for v in m["vecinos"]) or any(v["fuente"].endswith("fila 10") for v in m["vecinos"]), "vecinos con fuente «mes fila N»")
vec = {v["texto"]: v for v in m["vecinos"]}
chk(vec.get("domicilios fin", {}).get("fuente") == "julio fila 631", "vecino «domicilios fin» ← «julio fila 631»")
# --meses
mj = M.minar(filas, {"jun", "jul", "ago"})
chk(mj["meses"] == ["2026-06", "2026-07", "2026-08"] and mj["lexico"]["domicilios"]["n"] == 3, "--meses jun,jul,ago deja fuera septiembre")
chk(M.minar(filas, hasta="2026-07")["meses"] == ["2026-06", "2026-07"], "--hasta 2026-07")
with tempfile.TemporaryDirectory() as d:
    try: M.main(["--meses", "jun"]); chk(False, "con --meses sin --salida debe fallar")
    except SystemExit: chk(True, "con --meses sin --salida se niega a pisar el modelo de producción")

PERSONAS = {"luisa", "perez", "pedro", "gomez", "marta", "sergio", "dylan", "omar", "fabian", "yorli", "yorly", "luis", "gabriel"}
def privado(modelo, extra=()):
    """palabra, proveedor y texto del vecino (no la cuenta ni la fuente «julio fila 631»): sin números ≥ 4 cifras, fechas ni personas."""
    s = " | ".join(list(modelo["lexico"]) + list(modelo["proveedores"]) + [v["texto"] for v in modelo["vecinos"]])
    toks = set(re.findall(r"[a-z]{3,}", M.norm(s)))
    return not re.search(r"\d{4,}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|20\d\d-\d\d", s) and not (toks & (PERSONAS | set(extra)))
chk(privado(m), "ADR-020/N5: dato personal o valor en el modelo (sintético)")
# el valor «12345» del texto y los nombres no se cuelan
chk("12345" not in json.dumps(m) and "luisa" not in json.dumps(m).lower(), "sin números del texto ni nombres de nómina")

if M.MANUAL.is_file():
    real = M.leer_filas()
    mp = M.minar(real)
    pers = M.personas(real)
    chk(len(mp["lexico"]) > 50 and len(mp["proveedores"]) > 10 and len(mp["vecinos"]) > 100, f"Excel real: {len(mp['lexico'])} palabras · {len(mp['proveedores'])} proveedores · {len(mp['vecinos'])} vecinos")
    chk(privado(mp, pers), "ADR-020/N5: dato personal o valor en el modelo (Excel real)")
    chk(all(re.fullmatch(r"\d{8}", v["cuenta"]) or re.fullmatch(r"\d{6,8}", v["cuenta"]) for v in mp["lexico"].values()), "cuentas con forma de código PUC")
    prod = M.SALIDA
    if prod.is_file():
        pj = json.loads(prod.read_text(encoding="utf8"))
        chk(privado(pj, pers), "ADR-020/N5: modelo_manual.json versionado sin datos personales")
else:
    print("(sin el Excel manual: se omite la parte real)")
print("\n" + ("TODO OK" if ok else "HAY FALLOS"))
sys.exit(0 if ok else 1)
