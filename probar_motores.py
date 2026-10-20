"""M-25 · motores Indra/Tesseract. T2: cliente C2 (ocr_module/indra.py) contra probar_motores_falso.py — responde, se cuelga, muere y miente.
Fitness de ADR-016. La parte de la fachada (ADR-017) llega con T3."""
import base64, hashlib, re, subprocess, sys, tempfile, threading, time
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

print(f"\n{'OK' if not fallos else f'{len(fallos)} FALLOS'}")
sys.exit(1 if fallos else 0)
