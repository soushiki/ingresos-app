"""Prueba de lectura de PDF (texto digital y páginas escaneadas) y del cierre del POS."""
import io, sys
from pathlib import Path
import pymupdf
from PIL import Image, ImageDraw
from ocr_module import pdf as pdflib
from parser_module.contable import construir, leer_texto
from parser_module.contable.ejemplos import VENTA

ok = True
def chk(c, m):
    global ok; ok &= bool(c); print(("✓ " if c else "✗ ") + m)

CIERRE = Path("parser_module/ejemplos_pos/recibo_foto3.txt").read_text(encoding="utf8")
# 1) PDF digital: etiqueta a la izquierda y valor a la derecha (como lo imprime un POS)
doc = pymupdf.open(); pg = doc.new_page(width=300, height=900); y = 30
for linea in CIERRE.splitlines():
    if not linea.strip(): continue
    partes = linea.rsplit("   ", 1) if "   " in linea else [linea]
    pg.insert_text((20, y), partes[0].strip(), fontsize=8)
    if len(partes) == 2: pg.insert_text((220, y), partes[1].strip(), fontsize=8)
    y += 10
digital = doc.tobytes()
# 2) PDF escaneado: la página es solo una imagen (sin capa de texto)
im = Image.new("RGB", (900, 1200), "white"); ImageDraw.Draw(im).text((40, 40), "papel escaneado", fill="black")
b = io.BytesIO(); im.save(b, "PNG"); d2 = pymupdf.open(); p2 = d2.new_page(width=450, height=600); p2.insert_image(p2.rect, stream=b.getvalue()); escaneado = d2.tobytes()
# 3) PDF mixto de 2 páginas
d3 = pymupdf.open(stream=digital, filetype="pdf"); d3.insert_pdf(pymupdf.open(stream=escaneado, filetype="pdf")); mixto = d3.tobytes()

i = pdflib.info(mixto)
chk(i["paginas"] == 2 and i["con_texto"] == [True, False], f"info: 2 páginas, con texto digital {i['con_texto']}")
t, img = pdflib.pagina(mixto, 1)
chk(t and img is None and "TOTAL VENTA EN EFECTIVO" in t, "página digital → se usa su texto (sin OCR, instantáneo y exacto)")
t2, img2 = pdflib.pagina(mixto, 2)
chk(t2 is None and img2[:4] == b"\x89PNG", "página escaneada → se convierte en imagen para el OCR")
t3, img3 = pdflib.pagina(mixto, 1, como_imagen=True)
chk(t3 is None and img3[:4] == b"\x89PNG", "opción «leer como imagen» también para PDF con texto")
try: pdflib.pagina(mixto, 9); chk(False, "página inexistente debía fallar")
except RuntimeError as e: chk("2 páginas" in str(e), f"página inexistente → «{e}»")
try: pdflib.info(b"no es un pdf"); chk(False, "archivo no PDF debía fallar")
except RuntimeError as e: chk("No pude abrir" in str(e), "archivo que no es PDF → mensaje claro")

# cierre leído desde el texto del PDF
docs = leer_texto(t)
chk(len(docs) == 1 and docs[0]["tipo"] == "cierre", f"el texto del PDF se reconoce como CIERRE: {[d['tipo'] for d in docs]}")
c = docs[0]; dat = c["datos"]
chk((dat["venta_efectivo"], dat["transferencias"], dat["propinas_total"], dat["base_caja"], dat["faltante_impreso"]) == (363500, 342250, 48100, 58200, -138950), f"cifras del cierre: efectivo {dat['venta_efectivo']:,} · app {dat['transferencias']:,} · propinas {dat['propinas_total']:,} · faltante {dat['faltante_impreso']:,}")
chk(c["fecha"] == "2026-08-11", f"fecha del cierre: {c['fecha']}")

# categorías: lo que subes en «cierre / comandas / gastos»
chk(leer_texto(VENTA, "comandas")[0]["tipo"] == "venta" and not leer_texto(VENTA, "comandas")[0]["avisos"], "una comanda subida en «comandas»: sin avisos")
x = leer_texto(VENTA, "gastos")[0]
chk(x["tipo"] == "venta" and any("Lo subiste como" in a for a in x["avisos"]), "una comanda subida en «gastos»: se avisa, no se esconde")
chk(leer_texto("texto raro con 10.000 y nada más reconocible", "gastos")[0]["tipo"] == "factura", "papel irreconocible subido en «gastos» → factura para que lo completes")

# cruces cierre ↔ comandas
cierre = {"total_vendido": 178000, "venta_efectivo": 82200, "tarjetas_sin_prop": 95800, "propinas_total": 17800, "propinas_efectivo": 17800, "transacciones": 1, "factura_inicial": 85531, "factura_final": 85531}
vv = leer_texto(VENTA)
r = construir("2026-09-12", vv, {}, None, cierre)
chk(r["cruces"] and all(x["ok"] for x in r["cruces"]), f"cierre = comanda #85531 (efectivo 82.200 · tarjeta 95.800 · propina 17.800): {[x['concepto'][:12] + ' ✓' for x in r['cruces']]}")
r2 = construir("2026-09-12", vv, {}, None, {**cierre, "venta_efectivo": 182200, "total_vendido": 278000})
chk(any(not x["ok"] and x["diferencia"] == 100000 for x in r2["cruces"]) and any("no coincide" in a for a in r2["avisos"]), "si al cierre le sobran 100.000, avisa que falta una comanda")
r3 = construir("2026-09-12", docs + vv, {}, None, None)
chk(r3["cierre"]["venta_efectivo"] == 363500 and len(r3["filas"]) == 3, "el cierre leído de un papel alimenta los cruces y no genera asientos propios")
print("\n" + ("TODO OK" if ok else "HAY FALLOS"))
