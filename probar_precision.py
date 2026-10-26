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
# Avance: una corrida cortada (PC apagado) se reanuda sin releer las fotos hechas, y al terminar el avance se borra
def cortada(r, p, m):
    if Path(r).name == "h2.jpg": raise KeyboardInterrupt
    return leer_hoja(r, p, m).replace("\n====\n", f"\n{D.MARCA}\n")
av = d / "referencia" / "informes" / "avance_2026-09_V5.json"
try: medir_precision.ejecutar("2026-09", d, None, cortada, datos=d, variante="V5"); chk(False, "la corrida cortada debía cortarse")
except KeyboardInterrupt: pass
chk(av.exists() and list(json.loads(av.read_text(encoding="utf-8"))) == ["h1.jpg"], "avance: la foto leída antes del corte queda guardada")
leidas = []
inf5 = medir_precision.ejecutar("2026-09", d, None, lambda r, p, m: leidas.append(Path(r).name) or leer_hoja(r, p, m).replace("\n====\n", f"\n{D.MARCA}\n"), datos=d, variante="V5")
chk(leidas == ["h2.jpg"], f"avance: al reanudar solo se lee lo que faltaba (leídas {leidas})")
chk((inf5["omitidos"], inf5["validados_con_error_numeros"], inf5["por_campo"]) == (inf["omitidos"], inf["validados_con_error_numeros"], inf["por_campo"]),
    "avance: el informe reanudado es igual al de una corrida entera")
chk(not av.exists(), "avance: al terminar se borra")
leidas = []
try: medir_precision.ejecutar("2026-09", d, None, cortada, datos=d, variante="V5")
except KeyboardInterrupt: pass
medir_precision.ejecutar("2026-09", d, None, lambda r, p, m: leidas.append(Path(r).name) or leer_hoja(r, p, m), datos=d, variante="V5", reanudar=False)
chk(leidas == ["h1.jpg", "h2.jpg"], "--de-cero: ignora el avance y lee todo")
lib2 = json.loads((d / "libro.json").read_text(encoding="utf-8"))
dud = leer_texto(recibo(103, 1000), "comandas")[0]; dud["avisos"] = ["Falta la hora"]; dud["origen"] = "h2.jpg#1"
lib2["2026-09-16"]["documentos"].append(dud)
chk(medir_precision.mas_dudosas(lib2, ref, 1) == {("h2.jpg", 1)}, "--peores 1: la foto con más dudosos gana aunque tenga menos recibos")
chk(medir_precision.mas_dudosas(json.loads((d / "libro.json").read_text(encoding="utf-8")), ref, 1) == {("h1.jpg", 1)}, "--peores sin dudosos: empata y gana la de más recibos")
chk(inf2["total"] == (2 if leidas[0] == "h1.jpg" else 1), "--muestra: el total cuenta solo los recibos de las fotos elegidas")
# T16 · --completo: lee como la app (orientar → separar → leer_hoja con catálogo y dígitos); un «dudoso» se mide como dudoso
from PIL import Image
for n in ("h1.jpg", "h2.jpg"): Image.new("RGB", (40, 40), "white").save(d / n, "PNG")
llamadas = []
def hoja_falsa(trozos, motor, categoria, nombre, **kw):
    llamadas.append(dict(n=len(trozos), motor=motor, categoria=categoria, nombre=nombre, **kw))
    if len(llamadas) == 1 or nombre == "h1.jpg":
        a, b = leer_texto(recibo(100, 50000), "comandas")[0], leer_texto(recibo(101, 3000), "comandas")[0]
        b["estado"], b["motivos"] = "dudoso", ["Tesseract no ve el total"]
        return dict(documentos=[a, b])
    return dict(documentos=[])
dig = lambda im: {1}
leer_c, parsear_c = medir_precision.lector_completo({"PLATO": 50000}, dig, separar=lambda im, esperados=None: [im], preparar=lambda b, g: (b, 0), hoja=hoja_falsa)
h1 = huella(d / "libro.json")
infc = medir_precision.ejecutar("2026-09", d, "MOTOR", leer_c, datos=d, variante="completo", leer_texto=parsear_c)
chk(infc["variante"] == "completo" and Path(infc["archivo"]).stem.endswith("_completo"), "--completo: el informe dice completo")
chk(llamadas and llamadas[0]["catalogo"] == {"PLATO": 50000} and llamadas[0]["leer_digitos"] is dig and llamadas[0]["motor"] == "MOTOR", "--completo pasa catálogo, leer_digitos y motor a leer_hoja")
chk(infc["total"] == 3 and infc["dudosos"] == 1 and infc["dudosos_numeros"] == ["101"] and infc["omitidos"] == 1, "--completo: el estado dudoso de la relectura cuenta como dudoso")
chk(huella(d / "libro.json") == h1 == infc["huella_libro_antes"] == infc["huella_libro_despues"], "--completo tampoco toca el libro")
infp = medir_precision.ejecutar("2026-09", d, "MOTOR", leer_c, datos=d, variante="completo", leer_texto=parsear_c, peores=1)
chk(infp["peores"] == 1 and infp["total"] <= 2, "--completo funciona con --peores")
infm = medir_precision.ejecutar("2026-09", d, "MOTOR", leer_c, datos=d, variante="completo", leer_texto=parsear_c, muestra=1)
chk(infm["muestra"] == 1, "--completo funciona con --muestra")
# FIX-8 · R5: una página de un PDF de varias páginas no trae todo el lote del nombre → completa=False
blanca = Image.new("RGB", (40, 40), "white")
blanca.save(d / "largo.pdf", save_all=True, append_images=[blanca.copy()]); blanca.save(d / "corto.pdf")
llamadas.clear(); leer_c(d / "largo.pdf", 2, "MOTOR"); leer_c(d / "corto.pdf", 1, "MOTOR"); leer_c(d / "h1.jpg", 1, "MOTOR")
chk([c.get("completa") for c in llamadas] == [False, True, True], "--completo: PDF de varias páginas → completa=False; 1 página o foto → True")
# FIX-2 · dudoso se cuenta por `estado`, no por tener avisos: «Foto borrosa» en un recibo validado no es dudoso
from parser_module.contable.referencia import medir
def _doc(n, total, **extra):
    x = leer_texto(recibo(n, total), "comandas")[0]; x.update(extra); return x
ref2 = {"mes": "2026-09", "documentos": [{"numero": "100", "foto": "h1.jpg", "pagina": 1, "documento": _doc(100, 50000)},
                                          {"numero": "101", "foto": "h1.jpg", "pagina": 1, "documento": _doc(101, 30000)},
                                          {"numero": "102", "foto": "h1.jpg", "pagina": 1, "documento": _doc(102, 20000)}]}
leidos2 = [_doc(100, 50000, estado="validado", avisos=["Foto borrosa"]), _doc(101, 3000, estado="validado", avisos=["Foto borrosa"]),
           _doc(102, 20000, estado="dudoso", avisos=["Foto borrosa"], motivos=["x"])]
inf4 = medir(ref2, d, lambda r, p: "t", lambda t, c: leidos2)
chk(inf4["dudosos_numeros"] == ["102"], "FIX-2: solo el de estado dudoso cuenta como dudoso (avisos «Foto borrosa» validado no)")
chk(inf4["validados_con_error_numeros"] == ["101"], "FIX-2: validado con avisos suaves y campo distinto cuenta como validado con error")
chk(medir_precision.catalogo_del_libro(d / "nada.json") == medir_precision.catalogo_del_libro(d / "nada.json"), "catalogo_del_libro sin libro no falla")
# T8 · R4: causa de cada omitido (tipo / corte / número) y el informe la trae
from parser_module.contable.referencia import causa_de
pz = lambda *xs: [{"i": i, "tipo": t, "numero": n, "texto": ""} for i, (t, n) in enumerate(xs)]
chk(causa_de("85388", [], pz(("venta", "85387"), ("gasto", "85388")), ["85387", "85388"]) == "tipo", "causa_de: pieza con el número pero no venta → tipo")
chk(causa_de("85340", [], pz(("venta", "85334")), ["85334", "85340"]) == "corte", "causa_de: menos piezas que esperados → corte")
chk(causa_de("85340", [], pz(("venta", "85334")), None) == "corte", "causa_de: nombre no entendido → corte")
chk(causa_de("85411", [], pz(("venta", "85410"), ("venta", "85441")), ["85410", "85411"]) == "número", "causa_de: piezas completas y ninguna trae el número → número")
inf5 = medir(ref2, d, lambda r, p: "t", lambda t, c: [_doc(100, 50000)])
chk(inf5["omitidos"] == 2 and sum(inf5["por_causa"].values()) == inf5["omitidos"], "medir: suma de por_causa = omitidos")
chk([x["numero"] for x in inf5["omitidos_detalle"]] == ["101", "102"] and all(x["causa"] in ("tipo", "corte", "número") for x in inf5["omitidos_detalle"]), "medir: omitidos_detalle con causa por número")
chk(list(inf5["piezas"]) == ["h1.jpg"] and inf5["piezas"]["h1.jpg"][0]["numero"] == "100", "medir: guarda piezas por foto (tipo, número, texto)")
# M-26 · R2b: recuperados y recuperados_con_error
from parser_module.contable.relectura import RECUPERADO
rec = lambda d: {**d, "estado": "dudoso", "motivos": [RECUPERADO.replace("{}", "100")]}
inf6 = medir(ref2, d, lambda r, p: "t", lambda t, c: [rec(_doc(100, 50000)), rec(_doc(101, 3000)), _doc(102, 1)])
chk(inf6["recuperados"] == 2 and inf6["recuperados_numeros"] == ["100", "101"], "medir: recuperados = ventas con el motivo RECUPERADO")
chk(inf6["recuperados_con_error"] == 1 and inf6["recuperados_con_error_numeros"] == ["101"], "medir: recuperados_con_error = recuperados con algún campo distinto")
chk(inf5["recuperados"] == 0 and inf5["recuperados_con_error"] == 0, "medir: sin motivo RECUPERADO → 0 y 0")
print("\n" + ("TODO OK" if not fallos else f"{len(fallos)} FALLOS")); sys.exit(1 if fallos else 0)
