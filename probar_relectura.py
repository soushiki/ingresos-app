"""T7 · C5 leer_recibo con motor falso: cuenta llamadas, voto por campo, foto borrosa, tope de tiempo y recorte guardado.
    python probar_relectura.py"""
import sys, tempfile, threading
from pathlib import Path
from PIL import Image, ImageDraw
from parser_module.contable import relectura
from parser_module.contable.relectura import leer_recibo, TIEMPO_AGOTADO, BORROSA_SIN_PAR

fallos = []
def chk(cond, msg):
    print(("✓ " if cond else "✗ ") + msg)
    if not cond: fallos.append(msg)

def doc(**kw):
    d = dict(tipo="venta", numero="85560", hora="20:01", detalle="Mesa M2 · Mesero Yorlin", medio="Efectivo", items=[],
             subtotal=50000, descuento=5000, consumo=45000, domicilio=2000, propina=4500, pagado=60000, cambio=8500,
             efectivo=51500, tarjeta=0, transf=0, credito=0, cortesia=0, avisos=[])
    d.update(kw); return d

class Motor:
    """Devuelve los documentos de `salidas` en orden (el «texto» ya viene parseado) y cuenta llamadas."""
    nombre = "falso"
    def __init__(self, *salidas, error_en=None): self.salidas, self.n, self.error_en = list(salidas), 0, error_en
    def __call__(self, img):
        self.n += 1
        if self.error_en == self.n: raise RuntimeError("Ollama caído")
        return self.salidas[min(self.n, len(self.salidas)) - 1]

img = Image.new("RGB", (300, 500), "white"); dr = ImageDraw.Draw(img)
for i in range(30): dr.text((10, 15 * i + 5), "TOTAL %d" % (1000 + 37 * i), fill="black")
P = dict(parsear=dict, umbral=0)          # nítida a la fuerza; el «texto» del motor ya es el documento
malo = doc(cambio=8000)                   # pagado − cambio no cuadra

m = Motor(doc()); r = leer_recibo(img, m, **P)
chk(m.n == 1, "recibo que valida: 1 llamada (ADR-005: recibo válido releído)")
chk(r["estado"] == "validado" and r["motivos"] == [], "estado validado sin motivos")
chk([p["variante"] for p in r["lectura"]["pasadas"]] == ["V0"], "lectura anota la pasada V0")
chk(r["lectura"]["candidatos"]["consumo"] == [dict(valor=45000, variante="V0", motor="falso")], "candidato con valor, variante y motor (N4)")

m = Motor(malo); r = leer_recibo(img, m, **P)
chk(m.n == 4, f"dudoso que nunca valida: 1 + 3 relecturas = 4 llamadas (hubo {m.n})")
chk(r["estado"] == "dudoso" and r["motivos"], "queda dudoso con motivos (R7)")
chk(r["cambio"] == 8000, "valor más probable: el que se repite")

m = Motor(malo, doc()); r = leer_recibo(img, m, **P)
chk(m.n == 2 and r["estado"] == "validado" and r["cambio"] == 8500, "V1 valida: gana entero y se para en 2 llamadas")

m = Motor(malo, malo, malo, malo); r = leer_recibo(img, m, max_relecturas=1, **P)
chk(m.n == 2, "max_relecturas=1 → 2 llamadas")
m = Motor(malo); leer_recibo(img, m, max_relecturas=9, **P)
chk(m.n == 4, "max_relecturas nunca pasa de 3")

# Voto por campo: ninguno valida; propina 4500 ×2 vs 1000 ×1, hora 20:01 ×1 vs 20:07 ×2 …
a = doc(cambio=8000, propina=1000); b = doc(cambio=8000, hora="20:07"); c = doc(cambio=8000, hora="20:07"); dd = doc(cambio=7000, propina=1000, hora="")
m = Motor(a, b, c, dd); r = leer_recibo(img, m, **P)
chk(r["hora"] == "20:07" and r["cambio"] == 8000, "voto: mayoría por campo (hora 20:07, cambio 8000)")
chk(r["propina"] == 1000, "voto: empate 2–2 en propina → el de V0")
chk(r["estado"] == "dudoso", "voto sin candidato válido → dudoso")
chk([x["valor"] for x in r["lectura"]["candidatos"]["hora"]] == ["20:01", "20:07", "20:07", ""], "candidatos por pasada en orden V0–V3")

# Foto borrosa: aunque V0 valide, hace falta una segunda lectura que coincida
B = dict(parsear=dict, umbral=1e12)
m = Motor(doc()); r = leer_recibo(img, m, **B)
chk(m.n == 2 and r["estado"] == "validado", "borrosa: V0 y V1 coinciden → validado en 2 llamadas")
chk(r["lectura"]["borrosa"] and "Foto borrosa" in r["avisos"], "borrosa: aviso «Foto borrosa» y marca en lectura (R4)")
m = Motor(doc(), doc(propina=0, efectivo=47000, cambio=13000), malo, malo); r = leer_recibo(img, m, **B)
chk(m.n == 4 and r["estado"] == "dudoso" and r["motivos"] == [BORROSA_SIN_PAR] and r["propina"] == 4500,
    "borrosa: dos válidos distintos y ningún par → dudoso con el primero válido")
m = Motor(doc(), doc(propina=0, efectivo=47000, cambio=13000), doc(propina=0, efectivo=47000, cambio=13000)); r = leer_recibo(img, m, **B)
chk(m.n == 3 and r["estado"] == "validado" and r["propina"] == 0, "borrosa: gana el primer par que coincide (V1 = V2)")

# Tope de tiempo: cada llamada «tarda» 10 s en un reloj falso
class Reloj:
    t = 0.0
    def __call__(self): return self.t
reloj = Reloj()
class MotorLento(Motor):
    def __call__(self, img): reloj.t += 10; return super().__call__(img)
m = MotorLento(malo); r = leer_recibo(img, m, limite_s=15, reloj=reloj, **P)
chk(m.n == 2, f"tope 15 s con pasadas de 10 s: 2 llamadas (hubo {m.n})")
chk(r["estado"] == "dudoso" and r["motivos"][-1] == TIEMPO_AGOTADO, "tope → «dudoso: tiempo agotado»")
reloj.t = 0; m = MotorLento(doc()); r = leer_recibo(img, m, limite_s=5, reloj=reloj, **P)
chk(r["estado"] == "validado" and TIEMPO_AGOTADO not in r["motivos"], "la primera lectura siempre se hace; si valida no hay aviso de tiempo")
chk(r["lectura"]["segundos"] == 10, "lectura.segundos mide todo el recorte")

# Errores del motor
m = Motor(malo, error_en=2); r = leer_recibo(img, m, **P)
chk(m.n == 2 and r["estado"] == "dudoso" and "error" in r["lectura"]["pasadas"][-1], "error en una relectura: se para y queda anotado")
try: leer_recibo(img, Motor(doc(), error_en=1), **P); chk(False, "error en V0 sube")
except RuntimeError: chk(True, "error en V0 sube (como hoy)")

# Lock: dos hilos nunca llaman al motor a la vez
dentro, maximo, cerrojo = [0], [0], threading.Lock()
class MotorConcurrente(Motor):
    def __call__(self, img):
        with cerrojo: dentro[0] += 1; maximo[0] = max(maximo[0], dentro[0])
        threading.Event().wait(0.01)
        with cerrojo: dentro[0] -= 1
        return super().__call__(img)
hilos = [threading.Thread(target=leer_recibo, args=(img, MotorConcurrente(malo)), kwargs=P) for _ in range(4)]
for h in hilos: h.start()
for h in hilos: h.join()
chk(maximo[0] == 1, "MOTOR_LOCK: nunca hay dos llamadas al motor a la vez")

# Recorte guardado (C6) y parser real por defecto
with tempfile.TemporaryDirectory() as tmp:
    r = leer_recibo(img, Motor(doc()), carpeta=tmp, **P)
    chk(r["recorte"].endswith(".jpg") and (Path(tmp) / r["recorte"]).is_file(), "guarda el recorte y anota su nombre")
r = leer_recibo(img, Motor("RECIBO # 85560\nMESA: M2\nTOTAL CONSUMO $45.000"), umbral=0)
chk(r["numero"] == "85560" and r["estado"] == "dudoso" and "lectura" in r, "sin `parsear` usa parse_venta sobre el texto del motor")
chk("requests" not in relectura.__dict__, "relectura no habla con Ollama directo: todo pasa por `motor`")

print(f"\n{'FALLAS: ' + str(len(fallos)) if fallos else 'todo bien'}")
sys.exit(1 if fallos else 0)
