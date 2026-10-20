"""T8b + M-11: separar(img, esperados=n) parte las fotos de comandas (papeles en columnas, escalonados, con bordes que se tocan,
sobre mesa de madera u oscura, o la foto de lado)
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

# M-11: mesa de madera (vetas de color) debajo de los papeles: no cuenta como tinta ni sale como un papel vacío
madera = Image.new("RGB", (1050, 2000), (215, 160, 110)); d = ImageDraw.Draw(madera)
for y in range(0, 2000, 7): d.line((0, y, 1050, y + random.randint(-20, 20)), fill=(150, 95, 60), width=2)
d.rectangle((5, 5, 1045, 1605), fill=(245, 245, 245)); madera.paste(hoja.crop((0, 0, 1040, 1600)), (5, 5))
p = separar(madera, esperados=6)
check(len(p) == 6, f"sobre madera, esperados=6: 6 papeles (salieron {len(p)})")
check(all(im.height < 1000 for im in p), "ningún recorte se come la franja de madera de abajo")

lado = hoja.rotate(90, expand=True)                     # la foto de lado que el OSD no giró
p = separar(lado, esperados=6)
check(len(p) == 6, f"foto de lado, esperados=6: 6 papeles (salieron {len(p)})")
check(all(min(im.size) < 420 and max(im.size) > 400 for im in p), "de lado: cada recorte es un papel, no media fila")

solo = Image.new("RGB", (400, 1400), "white"); recibo(ImageDraw.Draw(solo), 20, 20, 360, 1350, 50)
check(len(separar(solo)) == 1, "un solo recibo largo sin esperados: una pieza")
check(len(separar(Image.new("RGB", (300, 300), "white"), esperados=4)) == 1, "hoja en blanco: la hoja entera")

# M-25 T6 (ADR-018): con `detectar` (Indra) la hoja se gira y se endereza; la hoja derecha no se toca.
import io
import numpy as np

def png_de(im): b = io.BytesIO(); im.save(b, "PNG"); return b.getvalue()

def inclinacion(im):
    """Ángulo (signo de PIL.rotate, paso 0,25°) que deja los renglones más horizontales: perfil de proyección."""
    chica = im.convert("L"); chica.thumbnail((500, 500))
    def nitidez(a): return np.asarray(chica.rotate(a, expand=True, fillcolor=255)).__lt__(128).sum(1).astype(float).var()
    return max(np.arange(-3, 3.01, 0.25), key=nitidez)

base = Image.new("RGB", (700, 1000), "white"); d = ImageDraw.Draw(base)
recibo(d, 20, 20, 660, 960, 40); d.rectangle((40, 40, 200, 120), fill="black")    # marca arriba a la izquierda
torcida = base.rotate(-8, expand=True, fillcolor="white").rotate(90, expand=True, fillcolor="white")   # de lado y 8° torcida
pedidos = []
def falso(im): pedidos.append(im.size); return 90, 1.0, 8.0
png, g = preparar_pagina(png_de(torcida), detectar=falso)
derecha = Image.open(io.BytesIO(png)).convert("L")
check(g == 90 and len(pedidos) == 1, f"detectar se pide una vez sobre la hoja completa y da el giro (g={g})")
check(derecha.height > derecha.width, f"girada 90° vuelve de pie ({derecha.size})")
check(abs(inclinacion(derecha)) <= 1, f"inclinada 8° queda derecha (resta {inclinacion(derecha)}°)")
a = np.asarray(derecha) < 128; h, w = a.shape
check(a[:h // 4, :w // 3].mean() > 2 * a[3 * h // 4:, 2 * w // 3:].mean(), "la marca queda arriba a la izquierda (no 270 ni 180)")

recta = png_de(base)
check(preparar_pagina(recta, detectar=lambda im: (0, 1.0, 0.2))[0] == preparar_pagina(recta, detectar=lambda im: (0, 0.0, 0.0))[0],
      "ADR-018: hoja derecha modificada (giro 0 e |incl| < 0,3° no se toca)")
check(preparar_pagina(recta, 0, detectar=falso)[1] == 0 and len(pedidos) == 1, "giro a mano: no se pregunta a detectar")
check(preparar_pagina(recta, detectar=lambda im: (90, 0.1, 0.0))[1] == 0, "confianza baja: no se gira (como con Tesseract)")

p = separar(lado, esperados=6, detectar=lambda im: (90, 1.0, 0.0))
check(len(p) == 6 and all(im.height > im.width for im in p), "de lado con detectar: los 6 papeles quedan de pie")

# Las fotos reales de septiembre (si la carpeta está): ≥ 80 % con la cuenta exacta del nombre (T8b midió 35/43).
raiz = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "data" / "SEPTIEMBRE"
fotos = [(f, n) for f in sorted(raiz.glob("*/comandas/*.jpg")) if (n := numeros_de_nombre(f.stem)) and len(n) >= 2]
if fotos:
    import io
    bien = 0
    for f, n in fotos:
        png, _ = preparar_pagina(f.read_bytes())
        bien += len(separar(Image.open(io.BytesIO(png)).convert("RGB"), esperados=len(n))) == len(n)
    check(bien >= 0.9 * len(fotos), f"fotos reales: {bien}/{len(fotos)} con la cuenta exacta (≥ 90 %; M-11 midió 42/43)")
else:
    print("     (sin la carpeta de fotos de septiembre: se salta la medición real)")
print(f"\n{ok} comprobaciones OK")
