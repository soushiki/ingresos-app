"""T5 · ADR-006: recortes por huella y ruta que solo sirve <16 hex>.jpg."""
import os, sys, tempfile
from datetime import date, timedelta
from pathlib import Path
from PIL import Image
from parser_module.contable import recortes
import app as appmod

fallos = []
def chk(cond, msg):
    print(("✓ " if cond else "✗ ") + msg)
    if not cond: fallos.append(msg)

tmp = Path(tempfile.mkdtemp())
a = Image.effect_noise((60, 40), 80).convert("RGB"); b = Image.effect_noise((60, 40), 30).convert("RGB")
n1, n2, n3 = recortes.guardar(a, tmp), recortes.guardar(a.copy(), tmp), recortes.guardar(b, tmp)
chk(n1 == n2, "misma imagen → mismo nombre")
chk(n1 != n3, "otra imagen → otro nombre")
chk(len(list(tmp.glob("*.jpg"))) == 2, "no duplica archivos")
chk(recortes.NOMBRE.fullmatch(n1) is not None, "nombre = 16 hex + .jpg")
chk(Image.open(__import__("io").BytesIO(recortes.abrir(n1, tmp))).mode == "L", "se guarda en gris")
chk(recortes.abrir("../x", tmp) is None and recortes.abrir("A" * 16 + ".jpg", tmp) is None, "abrir rechaza nombres raros")
chk(recortes.huerfanos([n1], tmp) == [n3], "huérfanos: lo que ningún documento usa")
hoy = date.today()
chk(recortes.borrar(hoy + timedelta(1), hoy + timedelta(2), tmp) == 0, "borrar fuera del rango no borra")
os.utime(tmp / n3, (0, 86400 * 365))   # 1971
chk(recortes.borrar(date(1970, 1, 1), date(1972, 1, 1), tmp) == 1 and not (tmp / n3).exists() and (tmp / n1).exists(), "borrar(desde, hasta) borra solo ese rango")

# ruta HTTP sobre una carpeta temporal
appmod.RUTA_RECORTES = tmp
c = appmod.app.test_client()
r = c.get(f"/api/contable/recorte/{n1}")
chk(r.status_code == 200 and r.mimetype == "image/jpeg" and r.data[:2] == b"\xff\xd8", "un recorte se sirve como image/jpeg")
for malo in ["..%2Flibro.json", "a.jpg", n1.upper(), "0123456789abcdef.jpg", n1[:-4], "..", n1 + "x"]:
    chk(c.get(f"/api/contable/recorte/{malo}").status_code == 404, f"404 para {malo}")

print("OK" if not fallos else f"FALLÓ {len(fallos)}")
sys.exit(1 if fallos else 0)
