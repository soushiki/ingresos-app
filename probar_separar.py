"""T8b: separar(img, esperados=n) parte las fotos de comandas (papeles en columnas, escalonados, con bordes que se tocan)
en un papel por recorte; sin `esperados` todo sigue como antes.
    python probar_separar.py [carpeta de fotos de septiembre, opcional]"""
import random, sys
from pathlib import Path
from PIL import Image, ImageDraw
from ocr_module.orientacion import separar, preparar_pagina
from parser_module.contable.validar import numeros_de_nombre

ok = 0
def check(cond, msg):
    global ok
    print(("OK   " if cond else "FALLA"), msg)
    if not cond: raise SystemExit(1)
    ok += 1


def recibo(d, x, y, w, h, renglones):
    """Un papel: borde gris (como la sombra de la foto) y renglones de «texto» con huecos chicos entre secciones."""
    d.rectangle((x, y, x + w, y + h), outline=(120, 120, 120), width=3)
    yy = y + 25
    for i in range(renglones):
        xx, fin = x + 15, x + 15 + random.randint(int(0.4 * w), int(0.75 * w))
        while xx < fin:                                   # palabras cortas con espacios, como la letra impresa
            p = random.randint(15, 45); d.rectangle((xx, yy, min(fin, xx + p), yy + 9), fill="black"); xx += p + 9
        yy += 22 + (14 if i % 6 == 5 else 0)
        if yy > y + h - 30: break


random.seed(3)
hoja = Image.new("RGB", (1050, 1600), (245, 245, 245)); d = ImageDraw.Draw(hoja)
for col, (x, desfase) in enumerate([(10, 0), (355, 60), (700, 25)]):     # 3 columnas pegadas, filas escalonadas
    alto1 = 680 + 40 * col
    recibo(d, x, 10 + desfase, 340, alto1, 26)
    recibo(d, x, 10 + desfase + alto1 + 3, 340, 1560 - alto1 - desfase - 20, 26)

check(len(separar(hoja)) <= 3, "sin esperados: el método de siempre no parte las filas que se tocan")
p = separar(hoja, esperados=6)
check(len(p) == 6, f"con esperados=6: 6 papeles (salieron {len(p)})")
check(all(150 < im.width < 420 for im in p), "cada recorte cabe en una columna (no junta dos papeles de lado)")
check(all(400 < im.height < 1000 for im in p), "cada recorte tiene el alto de un papel, no de la columna")
check(len(separar(hoja, esperados=8)) >= 1, "esperados de más no revienta")
check(len(separar(hoja, esperados=20)) >= 1, "esperados > max_papeles: vuelve al método de siempre")

solo = Image.new("RGB", (400, 1400), "white"); recibo(ImageDraw.Draw(solo), 20, 20, 360, 1350, 50)
check(len(separar(solo)) == 1, "un solo recibo largo sin esperados: una pieza")
check(len(separar(Image.new("RGB", (300, 300), "white"), esperados=4)) == 1, "hoja en blanco: la hoja entera")

# Las fotos reales de septiembre (si la carpeta está): ≥ 80 % con la cuenta exacta del nombre (T8b midió 35/43).
raiz = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "data" / "SEPTIEMBRE"
fotos = [(f, n) for f in sorted(raiz.glob("*/comandas/*.jpg")) if (n := numeros_de_nombre(f.stem)) and len(n) >= 2]
if fotos:
    import io
    bien = 0
    for f, n in fotos:
        png, _ = preparar_pagina(f.read_bytes())
        bien += len(separar(Image.open(io.BytesIO(png)).convert("RGB"), esperados=len(n))) == len(n)
    check(bien >= 0.8 * len(fotos), f"fotos reales: {bien}/{len(fotos)} con la cuenta exacta (≥ 80 %)")
else:
    print("     (sin la carpeta de fotos de septiembre: se salta la medición real)")
print(f"\n{ok} comprobaciones OK")
