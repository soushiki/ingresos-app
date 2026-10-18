"""T15 · R10, N5: exportar_entrenamiento (imagen + JSON) y borrar recortes por rango / huérfanos."""
import json, os, sys, tempfile
from datetime import date
from pathlib import Path
from PIL import Image
from parser_module.contable import recortes, referencia

fallos = []
def chk(cond, msg):
    print(("✓ " if cond else "✗ ") + msg)
    if not cond: fallos.append(msg)

tmp = Path(tempfile.mkdtemp()); rec = tmp / "recortes"; out = tmp / "export"
nombres = [recortes.guardar(Image.effect_noise((60, 40), s).convert("RGB"), rec) for s in (80, 30, 55)]
ref = {"mes": "2026-09", "documentos": [
    {"numero": "101", "foto": "a.jpg", "pagina": 1, "documento": {"numero": "101", "consumo": 5000, "recorte": nombres[0]}},
    {"numero": "102", "foto": "a.jpg", "pagina": 1, "documento": {"numero": "102", "consumo": 7000, "recorte": nombres[1]}},
    {"numero": "103", "foto": "b.jpg", "pagina": 1, "documento": {"numero": "103", "consumo": 1}}]}
r = referencia.exportar_entrenamiento(ref, rec, out)
chk(r["exportados"] == 2 and r["sin_recorte"] == ["103"], "exporta 2 recibos y cuenta el que no tiene recorte")
chk(len(list(out.glob("*.jpg"))) == 2 and len(list(out.glob("*.json"))) == 2, "una imagen y un JSON por recibo")
j = json.loads(next(out.glob("101_*.json")).read_text(encoding="utf-8"))
chk(j["documento"]["consumo"] == 5000 and (out / j["imagen"]).is_file(), "el JSON trae el documento corregido y apunta a su imagen")
chk(Image.open(out / j["imagen"]).size == (60, 40), "la imagen es el recorte")

os.utime(rec / nombres[1], (0, 86400 * 365))
chk(recortes.borrar(date(1970, 1, 1), date(1972, 1, 1), rec) == 1 and not (rec / nombres[1]).exists(), "borra un rango de fechas")
chk(recortes.borrar_huerfanos([nombres[0]], rec) == 1 and (rec / nombres[0]).exists() and not (rec / nombres[2]).exists(), "borra huérfanos y deja los usados")
print("OK" if not fallos else f"FALLÓ {len(fallos)}")
sys.exit(1 if fallos else 0)
