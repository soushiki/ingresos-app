"""T13 · C2 numeros_tesseract + R3 en validar. Imagen sintética; sin Tesseract → None y aviso."""
import io, sys, warnings
from unittest import mock
from PIL import Image, ImageDraw, ImageFont
from ocr_module import digitos
from ocr_module.digitos import numeros_tesseract
from parser_module.contable.validar import validar

fallos = []
def chk(cond, msg):
    print(("✓ " if cond else "✗ ") + msg)
    if not cond: fallos.append(msg)

try: f = ImageFont.truetype("arial.ttf", 40)
except Exception: f = ImageFont.load_default()
im = Image.new("L", (700, 260), 255); d = ImageDraw.Draw(im)
for i, t in enumerate(["85560", "45.000", "$ 60.000"]): d.text((30, 20 + i * 75), t, fill=0, font=f)
b = io.BytesIO(); im.save(b, "PNG")

v = numeros_tesseract(b.getvalue())
chk(v is not None and {85560, 45000, 60000} <= v, f"lee los números de la imagen sintética ({sorted(v or [])})")
chk(numeros_tesseract(im) is not None, "acepta también una imagen PIL")

digitos._avisado = False
with mock.patch.dict(sys.modules, {"pytesseract": None}), warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    chk(numeros_tesseract(b.getvalue()) is None, "sin Tesseract → None")
    chk(len(w) == 1 and "R3" in str(w[0].message), "sin Tesseract → aviso")

doc = dict(tipo="venta", numero="85560", hora="20:01", detalle="Mesa M2", medio="Efectivo", subtotal=50000, descuento=5000,
           consumo=45000, domicilio=0, propina=0, pagado=60000, cambio=15000, efectivo=45000)
chk(validar(doc, {"digitos": {85560, 45000, 60000}}) == [], "R3: todo aparece → sin motivos")
chk(validar(doc, {"digitos": None}) == [] and validar(doc) == [], "R3: None o ausente → se salta")
chk(validar(doc, {"digitos": {45000, 60000}}) == ["Tesseract no ve el número de recibo (85560) en la imagen"], "R3: falta número")
chk(validar(doc, {"digitos": {85560, 60000}}) == ["Tesseract no ve el total (45.000) en la imagen"], "R3: falta total")
chk(validar(doc, {"digitos": {85560, 45000}}) == ["Tesseract no ve lo pagado (60.000) en la imagen"], "R3: falta pagado")
chk(len(validar(doc, {"digitos": set()})) == 3, "R3: nada visto → tres motivos")
sys.exit(1 if fallos else 0)
