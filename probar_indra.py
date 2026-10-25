"""T9 · prueba de versión de Indra (C7, R7, N5). Con indra_venv instalado lanza el trabajador real y comprueba lo que la app usa de él;
sin venv se salta limpio. Si algo falla, indra-ocr cambió de salida: ver ADR-018 antes de actualizar la versión fijada."""
import sys, tempfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
from ocr_module import indra

fallos = []
def chk(cond, msg, si_falla=""):
    print(("✓ " if cond else "✗ ") + msg + ("" if cond or not si_falla else f" ({si_falla}; cambió la salida: ver ADR-018)"))
    if not cond: fallos.append(msg)

if not indra.disponible():
    print(f"- omitido: no hay {indra.python_venv()} (instalar_indra.bat); nada que probar")
    sys.exit(0)

from PIL import Image, ImageDraw, ImageFont
try:
    fuente = ImageFont.truetype("arial.ttf", 36)
except OSError:
    fuente = ImageFont.load_default(36)
hoja = Image.new("RGB", (900, 500), "white")
d = ImageDraw.Draw(hoja)
for i in range(8):
    d.text((40, 30 + 55 * i), f"Total venta {i+1}: $ {12345*(i+1):,} 2026-10-2{i}", font=fuente, fill="black")

c = indra.Cliente(log=Path(tempfile.mkdtemp(prefix="probar_indra_")) / "indra.log")
try:
    r = c.pedir("numeros", hoja)
    chk(c.version == "1.1.2", "saludo ready con versión 1.1.2", f"salió {c.version!r}")
    chk(isinstance(r.get("texto"), str) and "12,345" in r["texto"] and "98,760" in r["texto"],
        "numeros lee las cifras de un recorte de muestra", f"leyó {r.get('texto')!r}")
    chk(c.pedir("numeros", hoja)["texto"] == r["texto"], "dos lecturas del mismo recorte dan el mismo texto (N5)")

    u0 = c.pedir("upright", hoja)
    chk(u0["giro"] == 0, "upright de la hoja derecha da giro 0", f"dio {u0['giro']}")
    u90 = c.pedir("upright", hoja.rotate(-90, expand=True))   # 90° en sentido horario
    chk(u90["giro"] == 90, "upright de la hoja girada 90° da 90", f"dio {u90['giro']}")
    u90b = c.pedir("upright", hoja.rotate(-90, expand=True))
    chk((u90b["giro"], u90b["incl"]) == (u90["giro"], u90["incl"]), "dos lecturas de upright dan el mismo giro e inclinación (N5)")
except indra.IndraNoDisponible as e:
    chk(False, f"el trabajador contestó (ADR-018 si cambió la salida): {e}")
finally:
    c.cerrar()

print(f"\n{'FALLÓ' if fallos else 'OK'}: {len(fallos)} fallos")
sys.exit(1 if fallos else 0)
