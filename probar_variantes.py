"""C1: variantes(img) da 4 versiones con los tamaños esperados y nitidez(img) baja si la imagen está desenfocada.
    python probar_variantes.py"""
import random
from PIL import Image, ImageDraw, ImageFilter
from ocr_module.preprocess import variantes, nitidez

ok = 0
def check(cond, msg):
    global ok
    print(("OK   " if cond else "FALLA"), msg)
    if not cond: raise SystemExit(1)
    ok += 1

random.seed(1)
img = Image.new("RGB", (400, 600), "white")
d = ImageDraw.Draw(img)
for i in range(40):
    d.text((random.randint(0, 340), 12 * i + 5), "TOTAL %d" % random.randint(1000, 99999), fill="black")

v = variantes(img)
check(len(v) == 4, "4 variantes")
check([n for n, _ in v] == ["V0", "V1", "V2", "V3"], "nombres V0..V3")
check(v[0][1].size == (400, 600), "V0 conserva el tamaño")
check(v[1][1].size == (600, 900), "V1 es 1,5x")
check(v[2][1].size == (400, 600) and v[2][1].mode == "RGB", "V2 mismo tamaño, RGB")
r = v[2][1].convert("RGB").split()
check(r[0].tobytes()[:50] == r[1].tobytes()[:50], "V2 es gris (R=G)")
check(v[3][1].size == (400 - 2 * 12, 600 - 2 * 18), "V3 recorta 3 % por lado")
check(all(im.mode == "RGB" for _, im in v), "todas RGB")

n1 = nitidez(img)
n2 = nitidez(img.filter(ImageFilter.GaussianBlur(3)))
check(n2["laplaciano"] < n1["laplaciano"], "borrosa: menos Laplaciano")
check(n2["tenengrad"] < n1["tenengrad"], "borrosa: menos Tenengrad")
check(nitidez(Image.new("RGB", (50, 50), "white"))["laplaciano"] == 0, "imagen lisa = 0")
check(nitidez(Image.new("RGB", (2, 2)))["tenengrad"] == 0, "imagen diminuta no falla")

# T9 · variante(img, nombre) y V4 opcional (Real-ESRGAN)
import os, subprocess
from pathlib import Path
from ocr_module import preprocess as P
check(P.variante(img, "V1").size == (600, 900), "variante('V1') = V1")
try:
    P.variante(img, "V9"); check(False, "V9 debe fallar")
except ValueError:
    check(True, "variante desconocida → ValueError")
os.environ.pop("REALESRGAN", None); real = P.REALESRGAN; P.REALESRGAN = Path("no/existe.exe")
check(P._realesrgan_exe() is not None or P.superres(img) is None, "sin ejecutable V4 = None (nada falla)")
def falso(args, **kw):              # hace de realesrgan: escribe la salida ×4
    i, o = args[args.index("-i") + 1], args[args.index("-o") + 1]
    im = Image.open(i); im.resize((im.width * 4, im.height * 4)).save(o)
corre = subprocess.run; subprocess.run = falso
v4 = P.superres(img, exe=__file__)
check(v4 is not None and v4.size == (800, 1200) and v4.mode == "RGB", "V4 con ejecutable: ×2 en RGB")
def roto(args, **kw): raise subprocess.CalledProcessError(1, args)
subprocess.run = roto
check(P.superres(img, exe=__file__) is None, "V4 que falla → None, no excepción")
subprocess.run = corre; P.REALESRGAN = real
print(f"\n{ok} comprobaciones OK")
