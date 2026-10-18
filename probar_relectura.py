"""T7 · C5 leer_recibo con motor falso: cuenta llamadas, voto por campo, foto borrosa, tope de tiempo y recorte guardado.
    python probar_relectura.py"""
import sys, tempfile, threading
from pathlib import Path
from PIL import Image, ImageDraw
from parser_module.contable import relectura
from parser_module.contable.relectura import leer_recibo, TIEMPO_AGOTADO, BORROSA_SIN_PAR

ORDEN_T9 = list(relectura.CONFIG["variantes"])
relectura.CONFIG["variantes"] = ["V0", "V1", "V2", "V3"]   # el voto se prueba con V0–V3 fijas (V4 depende del ejecutable)

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

# T9 · el orden de las pasadas sale de la config; una variante que no está (V4 sin ejecutable) se salta
chk(ORDEN_T9[:2] == ["V0", "V4"] and "V2" in ORDEN_T9, "config T9: V0, luego V4; V2 de reserva")
import ocr_module.preprocess as P
_super = P.superres; P.superres = lambda im, **k: None
relectura.CONFIG["variantes"] = ["V0", "V4", "V3", "V1"]
chk([v for v, _ in relectura._pasadas(img, 3)] == ["V0", "V3", "V1"], "sin Real-ESRGAN, V4 se salta y entra la siguiente")
P.superres = lambda im, **k: im.resize((im.width * 2, im.height * 2))
chk([(v, i.width) for v, i in relectura._pasadas(img, 2)] == [("V0", 300), ("V4", 600)], "con Real-ESRGAN, V4 es la 2.ª pasada (×2)")
P.superres = _super; relectura.CONFIG["variantes"] = ["V0", "V1", "V2", "V3"]
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

# T8 · leer_hoja: varios recortes de una foto, números del nombre (R5), re-segmentar y vecinos
from parser_module.contable.relectura import leer_hoja
def rec(numero, mesa="M20", total=113000, hora="5:19:54 p. m."):
    return (f"SU RESTAURANTE\nRECIBO #: {numero}\nFecha de Venta: 16/09/2026 {hora}\nMesa: {mesa}\nMesero: YORLIN\n"
            f"SUBTOTAL CONSUMO | ${total:,}\n**TOTAL CONSUMO>> | ${total}\nDESCUENTO | $\n*TOTAL A PAGAR> | ${total:,}\n"
            f"PROPINA | $\nPAGADO | ${total:,}\nPAGA CON CREDITO | ${total:,}\nCAMBIO | $\n")
def trozo(i): return Image.new("RGB", (200 + 1000 * i, 400), "white")
class MotorHoja:
    """Recorte i (por su ancho, también en V1 ×1,5 y V3 −6 %) → sus textos en orden de llamada."""
    nombre = "falso"
    def __init__(self, **textos): self.textos, self.n, self.vistos = textos, 0, {}
    def __call__(self, img):
        self.n += 1
        i = next(i for i in range(9) if img.width in (200 + 1000 * i, round((200 + 1000 * i) * 1.5), 200 + 1000 * i - 2 * round((200 + 1000 * i) * 0.03)))
        k = self.vistos[i] = self.vistos.get(i, 0) + 1; t = self.textos[f"t{i}"]
        return t[min(k, len(t)) - 1] if isinstance(t, list) else t
H = dict(categoria="comandas", umbral=0, tope_s=1e9)   # motor falso instantáneo: T ≈ 0, el tope real se prueba al final

m = MotorHoja(t0=rec(85627), t1=rec(85628, "M3", 50000))
with tempfile.TemporaryDirectory() as tmp:
    h = leer_hoja([trozo(0), trozo(1)], m, nombre="16 SEPT/COMANDA/85627 al 628.jpg", carpeta=tmp, **H)
    chk(m.n == 2 and [d["estado"] for d in h["documentos"]] == ["validado"] * 2 and h["avisos"] == [], "foto que cuadra: 1 llamada por recorte, todo validado")
    chk(all((Path(tmp) / d["recorte"]).is_file() for d in h["documentos"]), "cada recibo con su recorte guardado")
chk(h["texto"].count("=== DOCUMENTO ===") == 1 and "85628" in h["texto"], "el texto de la hoja une los recortes con MARCA")

m = MotorHoja(t0=rec(85627), t1=[rec(85638, "M3", 50000), rec(85628, "M3", 50000)])
h = leer_hoja([trozo(0), trozo(1)], m, nombre="85627 al 628.jpg", **H); d = h["documentos"][1]
chk(m.n == 3 and d["numero"] == "85628" and d["estado"] == "validado", "número fuera del nombre → se relee y la V1 lo corrige")

m = MotorHoja(t0=rec(85627), t1=rec(85638, "M3", 50000))
h = leer_hoja([trozo(0), trozo(1)], m, nombre="85627 al 628.jpg", **H)
chk(h["documentos"][1]["motivos"][0] == "El recibo 85638 no está en el nombre de la foto (85627, 85628)" and m.n == 5,
    "sigue fuera tras 3 relecturas → dudoso con el motivo")
chk(h["avisos"] == ["Falta el recibo 85628 en esta foto"] and h["avisos"][0] in h["documentos"][0]["avisos"], "y avisa el que falta (R5)")

partes = lambda img: [trozo(1), trozo(2)] if img.width == 200 else [img]
m = MotorHoja(t0=rec(85627), t1=rec(85627), t2=rec(85628, "M3", 50000))
h = leer_hoja([trozo(0)], m, nombre="85627 al 628.jpg", separar=partes, **H)
chk([d["numero"] for d in h["documentos"]] == ["85627", "85628"] and h["avisos"] == [], "falta uno → re-segmenta, relee y aparece")
m = MotorHoja(t0=rec(85627))
h = leer_hoja([trozo(0)], m, nombre="85627 al 628.jpg", separar=lambda img: [img], **H)
chk(h["avisos"] == ["Falta el recibo 85628 en esta foto"] and m.n == 1, "si re-segmentar no parte nada, solo el aviso")
h = leer_hoja([trozo(0)], MotorHoja(t0=rec(85627)), nombre="85627 al 628.jpg", completa=False, **H)
chk(h["avisos"] == [], "página de un PDF con más páginas: no se reclaman faltantes")
h = leer_hoja([trozo(0)], MotorHoja(t0=rec(85627)), nombre="IMG_20260916_123456.jpg", **H)
chk(h["avisos"] == [] and h["documentos"][0]["estado"] == "validado", "nombre sin números de recibo: sin R5")

m = MotorHoja(t0=rec(85627), t1=rec(85628, "M3"))
h = leer_hoja([trozo(0), trozo(1)], m, nombre="85627 al 628.jpg", **H)
chk(all(d["estado"] == "dudoso" and d["motivos"][-1].endswith("posible cruce de valores") for d in h["documentos"]), "vecinos con montos idénticos y otra mesa → ambos dudosos")

m = MotorHoja(t0=rec(85627) + rec(85628, "M3", 50000))
h = leer_hoja([trozo(0)], m, nombre="85627 al 628.jpg", **H)
chk(m.n == 1 and len(h["documentos"]) == 2 and all(d["estado"] == "validado" for d in h["documentos"]), "dos recibos pegados en un texto: se parten como hoy y se validan sin releer")
m = MotorHoja(t0="CAJA MENOR\nTAXI 12.000\nTOTAL 12.000")
h = leer_hoja([trozo(0)], m, categoria="gastos", nombre="gastos_239.jpg", umbral=0)
chk(m.n == 1 and "estado" not in h["documentos"][0], "gastos: sin relectura ni estado")

reloj.t = 0
class MotorHojaLento(MotorHoja):
    def __call__(self, img): reloj.t += 10; return super().__call__(img)
m = MotorHojaLento(t0=rec(85637), t1=rec(85638, "M3", 50000))   # los dos fuera del nombre
h = leer_hoja([trozo(0), trozo(1)], m, nombre="85627 al 628.jpg", reloj=reloj, categoria="comandas", umbral=0); d = h["documentos"][1]
chk(m.n == 6 and h["segundos"] == 60, f"tope de la hoja = 3 × T: 20 s de V0 → 60 s; el 1.º usa sus 3 relecturas y al 2.º le alcanza 1 (hubo {m.n} llamadas)")
chk(TIEMPO_AGOTADO in d["motivos"] and TIEMPO_AGOTADO not in h["documentos"][0]["motivos"] and d["lectura"]["pasadas"][0]["segundos"] == 10, "al pasar el tope: «tiempo agotado»; V0 anota sus segundos")

print(f"\n{'FALLAS: ' + str(len(fallos)) if fallos else 'todo bien'}")
sys.exit(1 if fallos else 0)
