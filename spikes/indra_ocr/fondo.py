"""T5 spike XS (riesgo 2 de 03): fondo blanco con PIL.rotate(expand, fillcolor blanco) vs. BORDER_REPLICATE del spike.
Sin Indra ni cv2 (el venv del spike ya no existe): se inclina una hoja a 8/25/45°, se corrige con el mismo ángulo por cada método
y se mide (a) la inclinación residual con perfil de proyección (ángulo que maximiza la varianza de la suma por filas, ±3°, paso 0,25°),
relativa a la de la hoja original, y (b) cuántos recortes da recortar+separar frente a la original. Uso: python fondo.py"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image

APP = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(APP))
from ocr_module import orientacion

FOTOS = Path(r"D:\Claude\image_to_text\data\SEPTIEMBRE")
HOJAS = ["3/comanda/85330-331-333-335 al 337.jpg", "13/comandas/10-09-2026.jpg", "8/comandas/85467 al 473.jpg"]
ANGULOS = [8, 25, 45]


def inclinacion(img):
    """Grados que hay que girar (PIL, antihorario) para dejar las líneas de texto horizontales."""
    g = img.convert("L"); g.thumbnail((700, 700))
    tinta = (np.asarray(g, dtype=float) < 165)
    mejor, v_max = 0.0, -1.0
    for a in np.arange(-3, 3.01, 0.25):
        r = np.asarray(Image.fromarray((tinta * 255).astype("uint8")).rotate(a, resample=Image.BILINEAR), dtype=float)
        v = r.sum(1).var()
        if v > v_max: mejor, v_max = float(a), v
    return mejor


def corregir_blanco(img, a):
    return img.rotate(-a, expand=True, fillcolor="white", resample=Image.BICUBIC)


def corregir_replicar(img, a):
    """Imita warpAffine(BORDER_REPLICATE) del spike: mismo tamaño, borde = último píxel."""
    m = max(img.size)
    p = Image.fromarray(np.pad(np.asarray(img), ((m, m), (m, m), (0, 0)), mode="edge"))
    r = p.rotate(-a, resample=Image.BICUBIC)
    return r.crop((m, m, m + img.width, m + img.height))


def recortes(img):
    return len(orientacion.separar(orientacion.recortar(img)))


if __name__ == "__main__":
    for h in HOJAS:
        base = Image.open(FOTOS / h).convert("RGB"); base.thumbnail((1800, 1800))
        s0, n0 = inclinacion(orientacion.recortar(base)), recortes(base)
        for a in ANGULOS:
            t = base.rotate(a, expand=True, fillcolor="white", resample=Image.BICUBIC)
            fila = [f"{Path(h).name[:22]:22} {a:>2}° orig(incl {s0:+.2f}, recortes {n0})"]
            for nom, f in (("blanco", corregir_blanco), ("replicar", corregir_replicar)):
                c = f(t, a)
                fila.append(f"{nom}: resid {abs(inclinacion(orientacion.recortar(c)) - s0):.2f}° recortes {recortes(c)}")
            print(" | ".join(fila))
