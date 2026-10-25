"""M-25 · motores Indra/Tesseract. T2: cliente C2 (ocr_module/indra.py) contra probar_motores_falso.py — responde, se cuelga, muere y miente.
Fitness de ADR-016. La parte de la fachada (ADR-017) llega con T3."""
import base64, hashlib, io, re, subprocess, sys, tempfile, threading, time
from pathlib import Path
from unittest import mock

fallos = []
def chk(cond, msg):
    print(("✓ " if cond else "✗ ") + msg)
    if not cond: fallos.append(msg)

AQUI = Path(__file__).resolve().parent
FALSO = AQUI / "probar_motores_falso.py"
TMP = Path(tempfile.mkdtemp(prefix="probar_motores_"))
LOG = TMP / "indra.log"

# ADR-016: importar no arranca nada
with mock.patch("subprocess.Popen") as popen:
    from ocr_module import indra
    from ocr_module.indra import Cliente, IndraNoDisponible
    chk(not popen.called, "importar ocr_module.indra no arranca procesos (ADR-016: el trabajador arrancó al importar)")

# ADR-016: nada de la app (fuera del trabajador) carga Indra en su proceso
prohibido = re.compile(r"^\s*(import|from)\s+(indra_ocr|onnxruntime|cv2)\b", re.M)
malos = [str(p.relative_to(AQUI)) for p in AQUI.rglob("*.py")
         if not ({"spikes", "indra_venv", ".venv", "venv"} & set(p.relative_to(AQUI).parts)) and p.name != "indra_worker.py"
         and prohibido.search(p.read_text(encoding="utf-8", errors="ignore"))]
chk(not malos, f"ningún archivo de la app importa indra_ocr/onnxruntime/cv2 (ADR-016: la app cargó Indra en su proceso) {malos}")

N = [0]
def falso(modos, timeout_s=1.0, arranque_s=3.0):
    """Cliente contra el trabajador falso; cuenta arranques en su propio archivo."""
    N[0] += 1
    cont = TMP / f"cont{N[0]}"
    c = Cliente(python=sys.executable, trabajador=FALSO, timeout_s=timeout_s, arranque_s=arranque_s, log=LOG,
                env={"FALSO_MODOS": modos, "FALSO_CONTADOR": str(cont)})
    return c, (lambda: int(cont.read_text()) if cont.exists() else 0)

def falla(c, op="numeros", img=b"png"):
    """Tiempo que tardó el pedido en fallar, o None si no lanzó IndraNoDisponible."""
    t = time.monotonic()
    try: c.pedir(op, img)
    except IndraNoDisponible: return time.monotonic() - t
    return None

# sin venv → no disponible y no arranca nada
vacio = TMP / "vacio"; vacio.mkdir()
with mock.patch.dict("os.environ", {"INDRA_VENV": str(vacio)}):
    chk(indra.disponible() is False, "INDRA_VENV vacío → disponible() es False")
    with mock.patch("subprocess.Popen") as popen:
        c = Cliente(log=LOG)
        chk(falla(c) is not None and not popen.called, "sin venv → IndraNoDisponible sin arrancar procesos")
        chk(c.estado() == {"motor": "tesseract", "motivo": "sin venv"}, f"sin venv → estado tesseract «sin venv» ({c.estado()})")

# responde: arranque perezoso, un solo trabajador para varios pedidos
c, arranques = falso("ok")
chk(arranques() == 0 and c.estado()["motor"] == "indra", "crear el cliente no arranca el trabajador")
r = c.pedir("numeros", b"png")
chk(r.get("texto") == "85560 | 45.000", f"numeros → texto ({r})")
r = c.pedir("upright", b"png")
chk(r.get("giro") == 90 and r.get("incl") == 8.0, f"upright → giro 90, incl 8.0 ({r})")
from PIL import Image
r = c.pedir("numeros", Image.new("L", (40, 20), 255))
chk(r.get("texto") == "85560 | 45.000", "acepta también una imagen PIL")
chk(arranques() == 1, f"tres pedidos, un solo trabajador ({arranques()} arranques)")
p = c._p
c.cerrar()
chk(p.poll() is not None, "cerrar() termina el trabajador")
chk(falla(c, "otra") is not None, "op desconocida → IndraNoDisponible")

# se cuelga: se mata dentro del plazo y el siguiente pedido usa un trabajador nuevo
c, arranques = falso("cuelga,ok", timeout_s=1.0)
creados, popen_real = [], subprocess.Popen
def espia(*a, **k):
    creados.append(popen_real(*a, **k)); return creados[-1]
with mock.patch("subprocess.Popen", espia): t = falla(c)
p1 = creados[-1] if creados else None
chk(t is not None and t <= 1.0 + 1, f"colgado → IndraNoDisponible en ≤ timeout + 1 s ({t and round(t, 2)} s)")
chk(p1 is not None and p1.poll() is not None, "colgado → el proceso quedó muerto (ADR-016: trabajador colgado sin reiniciar)")
r = c.pedir("numeros", b"png")
chk(r.get("texto") == "85560 | 45.000" and arranques() == 2, f"tras colgarse, un trabajador nuevo contesta ({arranques()} arranques)")
chk(c.estado()["motor"] == "indra", "una falla y un acierto → sigue con Indra")
c.cerrar()

# muere dos veces seguidas → caído por la sesión, sin más arranques
c, arranques = falso("muere")
chk(falla(c) is not None and c.estado()["motor"] == "indra", "muere una vez → falla, pero sigue con Indra")
chk(falla(c) is not None, "muere otra vez → falla")
chk(c.estado() == {"motor": "tesseract", "motivo": "caído tras 2 fallas"}, f"2 fallas seguidas → caído por la sesión ({c.estado()})")
t = falla(c)
chk(t is not None and t < 0.5 and arranques() == 2, f"caído → falla al instante y no arranca otro ({arranques()} arranques)")

# un acierto entre fallas reinicia la cuenta
c, arranques = falso("muere,ok,ok")
falla(c); c.pedir("numeros", b"png"); c._p.kill(); c._p.wait()
chk(falla(c) is not None and c.estado()["motor"] == "indra", "falla, acierto, falla → no se apaga (las fallas son seguidas)")
c.cerrar()

# miente: giro 45, texto que no es str → cuenta como falla
c, _ = falso("miente")
chk(falla(c, "upright") is not None, "upright con giro 45 → IndraNoDisponible")
chk(falla(c, "numeros") is not None, "numeros con texto no str → IndraNoDisponible")
chk(c.estado()["motor"] == "tesseract", "dos mentiras → caído por la sesión")

# basura y mudo
c, _ = falso("basura")
chk(falla(c) is not None, "línea que no es JSON → IndraNoDisponible")
c.cerrar()
c, _ = falso("mudo", arranque_s=1.0)
t = falla(c)
chk(t is not None and t <= 1.0 + 1, f"no saluda → falla en ≤ arranque + 1 s ({t and round(t, 2)} s)")
falla(c)
chk(c.estado() == {"motor": "tesseract", "motivo": "falló el arranque"}, f"dos arranques fallidos → «falló el arranque» ({c.estado()})")

# N4: dos hilos a la vez no mezclan respuestas
c, arranques = falso("eco", timeout_s=5.0)
malas = []
def hilo(k):
    for i in range(15):
        img = f"img-{k}-{i}".encode()
        esperado = hashlib.sha1(base64.b64encode(img)).hexdigest()[:12]
        try:
            if c.pedir("numeros", img).get("texto") != esperado: malas.append((k, i))
        except IndraNoDisponible as e: malas.append((k, i, str(e)))
hs = [threading.Thread(target=hilo, args=(k,)) for k in range(3)]
for h in hs: h.start()
for h in hs: h.join(30)
chk(not malas and arranques() == 1, f"N4: 3 hilos × 15 pedidos, cada uno recibe su respuesta ({malas[:3]})")

# ADR-016: cerrar stdin termina el trabajador (EOF)
p = c._p
p.stdin.close()
try: p.wait(5); fin = True
except subprocess.TimeoutExpired: fin = False; p.kill()
chk(fin, "EOF en stdin → el trabajador termina en ≤ 5 s (ADR-016: trabajador huérfano)")
c.cerrar()

log = LOG.read_text(encoding="utf-8") if LOG.exists() else ""
chk(re.search(r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d .*caído", log, re.M) is not None, "logs/indra.log anota fallas y el apagado con la hora")

# ---------- T3 · fachada motores (ADR-017) ----------
import os
from ocr_module import digitos, orientacion, motores
TESS = {7, 8}
digitos.numeros_tesseract = lambda img: set(TESS)               # Tesseract «de siempre», determinista
orientacion.giro_automatico = lambda img: (180, 0.9)
im = Image.new("RGB", (60, 40), "white")
def usar(modos, **kw):
    c, _ = falso(modos, **kw); indra._cliente = c; return c

os.environ["INDRA_VENV"] = str(vacio); indra._cliente = None   # sin venv -> Tesseract + motivo
chk(motores.leer_digitos(im) == digitos.numeros_tesseract(im), "ADR-017: sin Indra no volvió a Tesseract")
e = motores.estado()
chk(e["motor"] == "tesseract" and e["motivo"] == "sin venv" and "Indra no disponible" in e["aviso"], f"sin venv: motor tesseract, motivo y aviso ({e})")
chk(motores.detectar_giro(im) == (180, 0.9, 0.0), "sin venv: detectar_giro -> (g, conf, 0.0) de Tesseract")

c = usar("ok")
chk(motores.estado() == {"motor": "indra", "motivo": None, "aviso": None}, "con venv: motor indra y sin aviso")
chk(motores.leer_digitos(im) == {85560, 45000}, "Indra: el texto pasa por digitos._enteros -> {85560, 45000}")
chk(motores.detectar_giro(im) == (90, 1.0, 8.0), "Indra: detectar_giro -> (90, 1.0, 8.0)")
c.cerrar()

c = usar("muere,ok")                                            # muere a mitad del pedido: esa foto sale por Tesseract
chk(motores.leer_digitos(im) == TESS, "ADR-017: foto perdida al caer Indra")
chk(c.fallas_seguidas == 1 and not c.caido and motores.estado()["motor"] == "indra", "una falla: todavía Indra")
chk(motores.leer_digitos(im) == {85560, 45000} and c.fallas_seguidas == 0, "la foto siguiente vuelve a Indra y borra la falla")
c.cerrar()

c = usar("muere,muere,ok")                                      # dos fallas -> Tesseract el resto de la sesión
a, b = motores.leer_digitos(im), motores.detectar_giro(im)
e = motores.estado()
chk(a == TESS and b == (180, 0.9, 0.0), "dos fallas: las dos llamadas dieron Tesseract")
chk(e["motor"] == "tesseract" and c.caido and "Indra caído" in e["aviso"], f"dos fallas: estado caído con aviso ({e})")
chk(motores.leer_digitos(im) == TESS and c._p is None, "caído: el resto de la sesión es Tesseract y no relanza el trabajador")

c = usar("miente")
chk(motores.leer_digitos(im) == TESS and motores.detectar_giro(im) == (180, 0.9, 0.0), "respuesta inválida -> Tesseract")
c.cerrar()

c = usar("eco", timeout_s=5.0)                                  # N4: dos hilos a la vez no mezclan respuestas
fotos = [Image.new("RGB", (60 + i, 40), "white") for i in range(2)]
def esp(f):
    b = io.BytesIO(); f.save(b, "PNG")
    return digitos._enteros(hashlib.sha1(base64.b64encode(b.getvalue())).hexdigest()[:12])
esperado, hechos, cruzadas = [esp(f) for f in fotos], [], []
def hilo(i):
    for _ in range(15):
        if motores.leer_digitos(fotos[i]) != esperado[i]: cruzadas.append(i)
    hechos.append(i)
ts = [threading.Thread(target=hilo, args=(i,)) for i in range(2)]
[t.start() for t in ts]; [t.join(60) for t in ts]
chk(len(hechos) == 2 and not cruzadas, f"N4: dos hilos a la vez no mezclan respuestas ({len(cruzadas)} cruzadas)")
c.cerrar()

for nombre in ("parser_module/contable/validar.py", "parser_module/contable/relectura.py"):
    t = (AQUI / nombre).read_text(encoding="utf-8")
    chk("motores" not in t and "indra" not in t, f"ADR-017: motor metido en las reglas ({nombre})")

# ---------- T10 · R5 de punta a punta: cierre del trabajador ----------
c, _ = falso("cuelga", timeout_s=8.0)                           # pedido colgado sostiene el candado
h = threading.Thread(target=lambda: falla(c), daemon=True); h.start()
for _ in range(50):
    if c._p is not None and c._candado.locked(): break
    time.sleep(0.1)
time.sleep(0.5)
p = c._p
t = time.monotonic(); c.cerrar(); dt = time.monotonic() - t
chk(p is not None and p.poll() is not None and dt <= 3, f"cerrar() con un pedido colgado mata el trabajador sin esperar el plazo ({dt:.1f} s)")
h.join(15)

# matar el proceso padre a la fuerza (sin atexit): el trabajador termina por EOF en ≤ 5 s
cont = TMP / "cont_padre"
codigo = ("import sys,os,time\nsys.path.insert(0,sys.argv[1])\nfrom ocr_module.indra import Cliente\nfrom pathlib import Path\n"
          "c=Cliente(python=sys.executable,trabajador=sys.argv[2],timeout_s=5,arranque_s=5,log=Path(sys.argv[3]),env={'FALSO_MODOS':'ok'})\n"
          "c.pedir('numeros',b'png');print(c._p.pid,flush=True);time.sleep(60)\n")
padre = subprocess.Popen([sys.executable, "-c", codigo, str(AQUI), str(FALSO), str(LOG)], stdout=subprocess.PIPE, text=True)
pid_hijo = int(padre.stdout.readline())
def vivo(pid):
    r = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True)
    return str(pid) in r.stdout
chk(vivo(pid_hijo), "el trabajador corre mientras vive la app")
padre.kill(); padre.wait(5)
t = time.monotonic()
while vivo(pid_hijo) and time.monotonic() - t < 6: time.sleep(0.2)
chk(not vivo(pid_hijo), f"R5: matar la app a la fuerza → el trabajador termina en ≤ 5 s ({time.monotonic() - t:.1f} s)")

print(f"\n{'OK' if not fallos else f'{len(fallos)} FALLOS'}")
sys.exit(1 if fallos else 0)
