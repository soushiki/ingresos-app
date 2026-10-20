"""Cliente del trabajador Indra (ADR-016). Corre en la app; el trabajador (indra_worker.py) corre en indra_venv (py 3.14).

Arranque perezoso (en el primer pedido, nunca al importar), un candado por pedido/respuesta (N4), plazos INDRA_ARRANQUE_S y
INDRA_TIMEOUT_S. Una falla (plazo vencido, proceso muerto, salida que no cuadra) mata el trabajador y lanza IndraNoDisponible;
el siguiente pedido arranca uno nuevo. Con 2 fallas seguidas queda apagado por la sesión (ADR-017 vuelve a Tesseract).
stderr del trabajador y cada falla/apagado van a logs/indra.log."""
import atexit, base64, io, json, math, os, queue, subprocess, sys, threading, time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
TRABAJADOR = Path(__file__).resolve().parent / "indra_worker.py"
LOG = RAIZ / "logs" / "indra.log"
GIROS = (0, 90, 180, 270)
MAX_LINEA = 1_000_000     # una respuesta más larga no es del trabajador
MAX_TEXTO = 50_000


class IndraNoDisponible(Exception):
    """Indra no puede contestar este pedido; quien llama usa Tesseract."""


def _venv():
    return Path(os.environ.get("INDRA_VENV") or RAIZ / "indra_venv")


def python_venv():
    return _venv() / "Scripts" / "python.exe"


def disponible():
    """Hay python.exe en el venv de Indra. No arranca nada."""
    return python_venv().is_file()


def _segundos(nombre, defecto):
    try:
        v = float(os.environ.get(nombre, defecto))
        return v if 0 < v < 3600 else defecto
    except ValueError:
        return defecto


def _png(img):
    """bytes (png/jpg) o imagen PIL -> base64 str."""
    if isinstance(img, (bytes, bytearray)):
        datos = bytes(img)
    else:
        b = io.BytesIO(); img.save(b, "PNG"); datos = b.getvalue()
    return base64.b64encode(datos).decode("ascii")


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _validar(op, r):
    """Respuesta del trabajador -> dict válido, o ValueError (cuenta como falla)."""
    if not isinstance(r, dict):
        raise ValueError("respuesta no es un objeto")
    if "error" in r:
        raise ValueError(f"el trabajador dijo: {str(r['error'])[:200]}")
    if op == "numeros":
        if not isinstance(r.get("texto"), str) or len(r["texto"]) > MAX_TEXTO:
            raise ValueError("texto inválido")
    elif op == "upright":
        if r.get("giro") not in GIROS or isinstance(r.get("giro"), bool):
            raise ValueError(f"giro inválido: {r.get('giro')!r}")
        if not _num(r.get("incl")) or abs(r["incl"]) > 45:
            raise ValueError(f"inclinación inválida: {r.get('incl')!r}")
    return r


class Cliente:
    def __init__(self, python=None, trabajador=TRABAJADOR, timeout_s=None, arranque_s=None, log=LOG, env=None):
        self.python = Path(python) if python else python_venv()
        self.trabajador = Path(trabajador)
        self.timeout_s = timeout_s or _segundos("INDRA_TIMEOUT_S", 10.0)
        self.arranque_s = arranque_s or _segundos("INDRA_ARRANQUE_S", 30.0)
        self.log = Path(log)
        self.env = env or {}
        self._candado = threading.Lock()
        self._p = self._q = self._err = None
        self.fallas_seguidas = 0
        self.caido = None          # motivo, si quedó apagado por la sesión
        self.version = None
        self._atexit = False

    # ---------- estado ----------
    def estado(self):
        if self.caido:
            return {"motor": "tesseract", "motivo": self.caido}
        if not self.python.is_file():
            return {"motor": "tesseract", "motivo": "sin venv"}
        return {"motor": "indra", "motivo": None}

    def _anotar(self, msg):
        try:
            self.log.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log, "a", encoding="utf-8") as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")
        except OSError:
            pass

    # ---------- proceso ----------
    def _arrancar(self):
        env = {**os.environ, **self.env, "HF_HUB_OFFLINE": "1", "HF_HUB_DISABLE_TELEMETRY": "1", "PYTHONIOENCODING": "utf-8"}
        env.setdefault("INDRA_OCR_MODEL_DIR", str(self.python.parent.parent / "modelos"))
        self.log.parent.mkdir(parents=True, exist_ok=True)
        self._err = open(self.log, "a", encoding="utf-8")
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        try:
            self._p = subprocess.Popen([str(self.python), "-I", str(self.trabajador)], stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE, stderr=self._err, text=True, encoding="utf-8",
                                       env=env, cwd=str(RAIZ), shell=False, creationflags=flags)
        except OSError as e:
            raise _Falla("falló el arranque", f"no se pudo lanzar {self.python.name}: {e}") from None
        self._q = queue.Queue()
        threading.Thread(target=self._leer, args=(self._p, self._q), daemon=True, name="indra-stdout").start()
        if not self._atexit:
            atexit.register(self.cerrar); self._atexit = True
        try:
            hola = json.loads(self._linea(self.arranque_s) or "null")
        except ValueError:
            hola = None
        if not (isinstance(hola, dict) and hola.get("ready") is True):
            raise _Falla("falló el arranque", f"sin saludo en {self.arranque_s:g} s")
        self.version = str(hola.get("version"))
        self._anotar(f"arrancó pid {self._p.pid}, indra-ocr {self.version}, carga {hola.get('load_s')} s")

    @staticmethod
    def _leer(p, q):
        try:
            while True:
                linea = p.stdout.readline(MAX_LINEA)
                if not linea:
                    break
                q.put(linea)
        except (OSError, ValueError):
            pass
        q.put(None)

    def _linea(self, plazo):
        """Siguiente línea del trabajador; None si se cerró o venció el plazo."""
        try:
            return self._q.get(timeout=plazo)
        except queue.Empty:
            return None

    def _matar(self):
        p, self._p = self._p, None
        if p is not None:
            try:
                p.kill(); p.wait(5)
            except (OSError, subprocess.TimeoutExpired):
                pass
            for s in (p.stdin, p.stdout):
                try: s.close()
                except (OSError, ValueError): pass
        if self._err is not None:
            self._err.close(); self._err = None

    def cerrar(self):
        """quit -> wait(5) -> kill. También corre con atexit."""
        with self._candado:
            p = self._p
            if p is None:
                return
            try:
                p.stdin.write('{"op":"quit"}\n'); p.stdin.flush(); p.stdin.close()
                p.wait(5)
            except (OSError, ValueError, subprocess.TimeoutExpired):
                pass
            self._matar()

    # ---------- pedidos ----------
    def pedir(self, op, img, timeout=None):
        """op ∈ {numeros, upright}, img = bytes o PIL -> dict validado. Lanza IndraNoDisponible."""
        if self.caido or not self.python.is_file():
            raise IndraNoDisponible(self.estado()["motivo"])
        if op not in ("numeros", "upright"):
            raise IndraNoDisponible(f"op desconocida: {op!r}")
        pedido = json.dumps({"op": op, "png": _png(img)}) + "\n"
        plazo = timeout or self.timeout_s
        if not self._candado.acquire(timeout=self.arranque_s + plazo + 5):
            raise IndraNoDisponible("ocupado")
        try:
            try:
                if self._p is None:
                    self._arrancar()
                elif self._p.poll() is not None:
                    raise _Falla("caído tras 2 fallas", f"el trabajador había salido ({self._p.returncode})")
                r = _validar(op, self._enviar(pedido, plazo))
            except (_Falla, ValueError, OSError) as e:
                motivo = e.motivo if isinstance(e, _Falla) else "caído tras 2 fallas"
                self._fallo(f"{op}: {e}", motivo)
                raise IndraNoDisponible(str(e)) from None
            self.fallas_seguidas = 0
            return r
        finally:
            self._candado.release()

    def _enviar(self, pedido, plazo):
        p = self._p
        perro = threading.Timer(plazo, lambda: p.poll() is None and p.kill())   # una escritura trabada también se corta
        perro.daemon = True
        t0 = time.monotonic(); perro.start()
        try:
            p.stdin.write(pedido); p.stdin.flush()
            linea = self._linea(max(0.0, plazo - (time.monotonic() - t0)))
        except (OSError, ValueError):
            linea = None
        finally:
            perro.cancel()
        if linea is None:
            vencido = time.monotonic() - t0 >= plazo
            raise _Falla("caído tras 2 fallas", f"no contestó en {plazo:g} s" if vencido else "el trabajador se cerró")
        return json.loads(linea)

    def _fallo(self, detalle, motivo):
        self._matar()
        self.fallas_seguidas += 1
        self._anotar(f"falla {self.fallas_seguidas}: {detalle}")
        if self.fallas_seguidas >= 2:
            self.caido = motivo
            self._anotar(f"Indra caído por la sesión ({motivo}); se usa Tesseract")


class _Falla(Exception):
    def __init__(self, motivo, detalle):
        super().__init__(detalle); self.motivo = motivo


_cliente = None
_cliente_candado = threading.Lock()


def cliente():
    """El Cliente de la app (uno por proceso). Crearlo no arranca el trabajador."""
    global _cliente
    with _cliente_candado:
        if _cliente is None:
            _cliente = Cliente()
        return _cliente
