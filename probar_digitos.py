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
from parser_module.contable.validar import notas_digitos
N = lambda v, **c: notas_digitos(doc, {**c, "digitos": v})
# R3b: no ver → nota suave, nunca motivo
chk(validar(doc, {"digitos": {45000, 60000}}) == [] and validar(doc, {"digitos": set()}) == [], "R3b: no ver ≠ dudoso (sin motivos)")
chk(N({45000, 60000}) == ["Sin confirmar por segundo lector: el número de recibo (85560)"], "R3b: nota del número")
chk(N({85560, 60000}) == ["Sin confirmar por segundo lector: el total (45.000)"], "R3b: nota del total")
chk(N({85560, 45000}) == ["Sin confirmar por segundo lector: lo pagado (60.000)"], "R3b: nota de lo pagado")
chk(len(N(set())) == 3 and N({85560, 45000, 60000}) == [] and N(None) == [] and notas_digitos(doc, None) == [], "R3b: nada visto → 3 notas; todo visto/None → ninguna")
# distinto con contexto → dudoso
m = validar(doc, {"digitos": {85561, 45000, 60000}, "esperados": [85560, 85561]})
chk(len(m) == 1 and "85561" in m[0] and "85560" in m[0], f"R3b: ve otro número del nombre de la foto → dudoso ({m})")
chk(validar(doc, {"digitos": {85561, 45000, 60000}}) == [] and validar(doc, {"digitos": {85561, 45000, 60000}, "esperados": [85560, 85562]}) == [],
    "R3b: sin contexto (o si el otro no está en el nombre) solo hay nota")
chk(validar(doc, {"digitos": {85560, 45000, 60000}, "esperados": [85560, 85561]}) == [], "R3b: ve el suyo además de otro → bien")
m = validar(doc, {"digitos": {85560, 30000, 60000}}); chk(m == [], "R3b: ve otro monto cualquiera → solo nota (las sumas ya son R1)")
sys.exit(1 if fallos else 0)
