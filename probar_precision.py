"""T1 · R9 / ADR-007: la medición contra la referencia congelada no escribe el libro. Motor falso, sin fotos ni OCR."""
import json, sys, tempfile
from pathlib import Path
from parser_module.contable import leer_texto
from parser_module.contable.referencia import huella
import medir_precision

fallos = []
def chk(cond, msg):
    print(("✓ " if cond else "✗ ") + msg)
    if not cond: fallos.append(msg)

def recibo(n, total, pago="PAGA CON CREDITO"):
    return (f"SU RESTAURANTE\nRECIBO #: {n}\nFecha de Venta: 16/09/2026 5:19:54 p. m.\nMesa: M2\nMesero: YORLIN\nDescripción | Cant | Valor\nPLATO | 1 | {total:,}\n"
            f"SUBTOTAL CONSUMO | ${total:,}\n**TOTAL CONSUMO>> | ${total}\nDESCUENTO | $\n*TOTAL A PAGAR> | ${total:,}\nPROPINA | $\nPAGADO | ${total:,}\n{pago} | ${total:,}\nCAMBIO | $")

TEXTOS = {"h1.jpg": [recibo(100, 50000), recibo(101, 30000)], "h2.jpg": [recibo(102, 20000)]}   # lo que "ve" el libro corregido
d = Path(tempfile.mkdtemp()); (d / "referencia").mkdir()
libro = {"2026-09-16": {"fecha": "2026-09-16", "documentos": [], "filas": []}, "2026-10-01": {"fecha": "2026-10-01", "documentos": []}}
for foto, rs in TEXTOS.items():
    for r in rs:
        doc = leer_texto(r, "comandas")[0]; doc["revisado"] = True; doc["origen"] = foto + "#1"; libro["2026-09-16"]["documentos"].append(doc)
otro = leer_texto(recibo(900, 1000), "comandas")[0]; otro["revisado"] = True; otro["fecha"] = "2026-10-01"; libro["2026-10-01"]["documentos"].append(otro)
(d / "libro.json").write_text(json.dumps(libro, ensure_ascii=False), encoding="utf-8")
h0 = huella(d / "libro.json")

# el lector falso: lee h1 con el recibo 101 mal (total 3.000 en vez de 30.000) y h2 vacío (omite 102)
def leer_hoja(ruta, pagina, motor):
    n = Path(ruta).name
    if n == "h1.jpg": return "\n" + "\n====\n".join([recibo(100, 50000), recibo(101, 3000)])
    return "foto ilegible"
import parser_module.contable.documentos as D
inf = medir_precision.ejecutar("2026-09", d, None, lambda r, p, m: leer_hoja(r, p, m).replace("\n====\n", f"\n{D.MARCA}\n"), datos=d)

chk(huella(d / "libro.json") == h0, "ADR-007: la medición tocó el libro (la huella debe ser igual)")
chk(inf["huella_libro_antes"] == inf["huella_libro_despues"] == h0, "el informe registra la misma huella antes y después")
ref = json.loads((d / "referencia" / "referencia_2026-09.json").read_text(encoding="utf-8"))
chk(len(ref["documentos"]) == 3 and ref["mes"] == "2026-09", "la referencia congela solo los 3 recibos revisados de septiembre")
chk(ref["documentos"][0]["foto"] == "h1.jpg" and ref["documentos"][0]["pagina"] == 1, "guarda la ruta de la foto y la página")
chk(inf["total"] == 3 and inf["omitidos"] == 1 and inf["omitidos_numeros"] == ["102"], "el recibo que no aparece cuenta como omitido")
chk(inf["validados_con_error"] == 1 and inf["validados_con_error_numeros"] == ["101"], "validado con error = sin avisos y algún campo distinto")
chk(inf["por_campo"]["consumo"] == {"ok": 1, "mal": 1, "acierto": 0.5}, "informe por campo (consumo 1 ok, 1 mal)")
chk(Path(inf["archivo"]).parent.name == "informes" and Path(inf["archivo"]).exists(), "el informe queda en referencia/informes/")
chk(len(list((d / "referencia").glob("referencia_*.json"))) == 1, "solo se escribió la referencia y el informe")

# T9 · la variante queda en el informe y en el nombre del archivo; comparar() arma una fila por variante
inf1 = medir_precision.ejecutar("2026-09", d, None, lambda r, p, m: leer_hoja(r, p, m).replace("\n====\n", f"\n{D.MARCA}\n"), datos=d, variante="V2")
chk(inf1["variante"] == "V2" and Path(inf1["archivo"]).stem.endswith("_V2"), "el informe dice la variante (V2) y el archivo termina en _V2")
chk(inf["variante"] == "V0" and not Path(inf["archivo"]).stem.endswith("_V0"), "V0 conserva el nombre de siempre")
cmp = medir_precision.comparar([inf, inf1])
chk([f["variante"] for f in cmp["variantes"]] == ["V0", "V2"] and cmp["variantes"][0]["omitidos"] == 1, "comparar: una fila por variante con omitidos")
chk(cmp["variantes"][1]["acierto"]["consumo"] == 0.5, "comparar: acierto por campo")
chk(huella(d / "libro.json") == h0, "con variantes tampoco se toca el libro")
leidas = []
inf2 = medir_precision.ejecutar("2026-09", d, None, lambda r, p, m: leidas.append(Path(r).name) or leer_hoja(r, p, m), datos=d, muestra=1, semilla=3)
inf3 = medir_precision.ejecutar("2026-09", d, None, lambda r, p, m: leidas.append(Path(r).name) or leer_hoja(r, p, m), datos=d, muestra=1, semilla=3)
chk(len(leidas) == 2 and leidas[0] == leidas[1] and inf2["muestra"] == 1, "--muestra 1: una sola foto, la misma con la misma semilla")
lib2 = json.loads((d / "libro.json").read_text(encoding="utf-8"))
dud = leer_texto(recibo(103, 1000), "comandas")[0]; dud["avisos"] = ["Falta la hora"]; dud["origen"] = "h2.jpg#1"
lib2["2026-09-16"]["documentos"].append(dud)
chk(medir_precision.mas_dudosas(lib2, ref, 1) == {("h2.jpg", 1)}, "--peores 1: la foto con más dudosos gana aunque tenga menos recibos")
chk(medir_precision.mas_dudosas(json.loads((d / "libro.json").read_text(encoding="utf-8")), ref, 1) == {("h1.jpg", 1)}, "--peores sin dudosos: empata y gana la de más recibos")
chk(inf2["total"] == (2 if leidas[0] == "h1.jpg" else 1), "--muestra: el total cuenta solo los recibos de las fotos elegidas")
print("\n" + ("TODO OK" if not fallos else f"{len(fallos)} FALLOS")); sys.exit(1 if fallos else 0)
