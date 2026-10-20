"""Indra vs Tesseract on the fixed 20-photo / 107-receipt set (same set as the qwen V0 report 20261018-040428), scored by the
project's own referencia.medir. Read-only for the project: writes only into this scratchpad (results/).
    python comparar.py indra-filas | indra-lineas | tesseract
One line per photo + checkpoint (results/avance_<motor>.json): re-run the same command to resume after the PC is turned off."""
import ctypes, io, json, re, sys, threading, time
from collections import Counter
from ctypes import wintypes
from pathlib import Path

APP = Path(r"D:\Claude\image_to_text\ingresos_app"); FOTOS = Path(r"D:\Claude\image_to_text\data\SEPTIEMBRE")
AQUI = Path(__file__).resolve().parent; RES = AQUI / "resultados"; RES.mkdir(exist_ok=True)
sys.path[:0] = [str(APP), str(AQUI)]
from PIL import Image
from ocr_module import digitize, get_engine, orientacion
from parser_module.contable import MARCA, leer_texto
from parser_module.contable.referencia import medir
from parser_module.contable.validar import numeros_de_nombre
import medir_precision

# ---- memory (Windows, no extra deps) -------------------------------------------------------------------------
class PMC(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t)] + [(f"x{i}", ctypes.c_size_t) for i in range(6)]
K = ctypes.WinDLL("kernel32"); K.OpenProcess.restype = wintypes.HANDLE; K.GetCurrentProcess.restype = wintypes.HANDLE
K.K32GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
def mem(h):
    p = PMC(); p.cb = ctypes.sizeof(PMC); K.K32GetProcessMemoryInfo(h, ctypes.byref(p), p.cb); return p.PeakWorkingSetSize / 2**20

class PE(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD), ("th32ProcessID", wintypes.DWORD), ("dflt", ctypes.c_size_t),
                ("mod", wintypes.DWORD), ("threads", wintypes.DWORD), ("parent", wintypes.DWORD), ("prio", ctypes.c_long),
                ("flags", wintypes.DWORD), ("exe", ctypes.c_char * 260)]
K.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
def vigilar_tesseract(pico, alto):
    """Polls every 30 ms the peak working set of each running tesseract.exe (pytesseract spawns one per call)."""
    while not alto.is_set():
        s = K.CreateToolhelp32Snapshot(2, 0); e = PE(); e.dwSize = ctypes.sizeof(PE); ok = K.Process32First(s, ctypes.byref(e))
        while ok:
            if e.exe.lower() == b"tesseract.exe":
                h = K.OpenProcess(0x1000 | 0x0010, False, e.th32ProcessID)
                if h: pico[0] = max(pico[0], mem(h)); K.CloseHandle(h)
            ok = K.Process32Next(s, ctypes.byref(e))
        K.CloseHandle(s); time.sleep(0.03)

# ---- the set ---------------------------------------------------------------------------------------------------
ref = json.loads((APP / "datos/referencia/referencia_2026-09.json").read_text(encoding="utf-8"))
sub = set(json.loads((APP / "datos/referencia/google/subconjunto.json").read_text(encoding="utf-8")))
fotos = {(r["foto"], r["pagina"]) for r in ref["documentos"] if r["numero"] in sub}
ref = {**ref, "documentos": [r for r in ref["documentos"] if (r["foto"], r["pagina"]) in fotos]}
assert len(fotos) == 20 and len(ref["documentos"]) == 107, (len(fotos), len(ref["documentos"]))

import difflib
RECIBO = re.compile(r"^\W*([A-Za-z0-9]{4,7})\s*\S{0,2}\s*:?\s*(\d{5})\W*$")
def rotulos(texto):
    """'+rotulos' variant (harness only, not in the app): a header line that looks like 'RECIBO #: 85366' with the word garbled
    (REC1BO, REC180, RECBO e …) is rewritten as 'RECIBO #: 85366', so the parser's strict 'recibo\\s*#' finds it. Digits untouched."""
    out = []
    for l in texto.splitlines():
        m = RECIBO.match(l)
        if m and difflib.SequenceMatcher(None, m.group(1).upper().replace("1", "I").replace("8", "B"), "RECIBO").ratio() >= 0.6:
            l = f"RECIBO #: {m.group(2)}"
        out.append(l)
    return "\n".join(out)

motor = sys.argv[1]; base, _, extra = motor.partition("+")
tiempos_p = RES / f"tiempos_{motor}.jsonl"
if base.startswith("indra"):
    from indra_cliente import Indra
    eng = Indra(threads=4, layout=base.split("-")[1]); leer_crudo = eng.texto
else:
    eng = get_engine("tesseract")
    def leer_crudo(t):
        b = io.BytesIO(); t.save(b, "PNG"); r = digitize(b.getvalue(), eng)
        if not r.ok: raise RuntimeError(r.error)
        return r.text
leer_trozo = (lambda t: rotulos(leer_crudo(t))) if extra == "rotulos" else leer_crudo
pico_t, alto = [0.0], threading.Event()
if base == "tesseract": threading.Thread(target=vigilar_tesseract, args=(pico_t, alto), daemon=True).start()

def leer_hoja(ruta, pagina):
    """= medir_precision.leer_hoja_v0 (orient → separate with expected count → OCR each piece), the OCR step swapped."""
    t0 = time.perf_counter()
    png, _ = orientacion.preparar_pagina(ruta.read_bytes(), "auto")
    esperados = numeros_de_nombre(ruta.stem) if ruta.parent.name in ("comandas", "comanda") else None
    trozos = orientacion.separar(Image.open(io.BytesIO(png)).convert("RGB"), esperados=len(esperados) if esperados else None)
    t1 = time.perf_counter(); out = [leer_trozo(t) for t in trozos]; t2 = time.perf_counter()
    with tiempos_p.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"foto": str(ruta.relative_to(FOTOS)), "trozos": len(trozos), "prep_s": round(t1 - t0, 2), "ocr_s": round(t2 - t1, 2)}) + "\n")
    return f"\n{MARCA}\n".join(out)

av = RES / f"avance_{motor}.json"
hechas = json.loads(av.read_text(encoding="utf-8")) if av.exists() else {}
if hechas: print(f"reanudo {av.name}: {len(hechas)} fotos ya leídas", flush=True)
inf = medir(ref, FOTOS, leer_hoja, leer_texto, hechas=hechas, al_leer=medir_precision._avance(av, hechas))
alto.set()
mem_engine = eng.cerrar()["peak_rss_mb"] if base.startswith("indra") else round(pico_t[0], 1)

# ---- extra fields: NIT and item lines (from each read receipt's text vs the reference receipt's reviewed text) ----
PRECIO = re.compile(r"\b\d{1,3}(?:[.,]\d{3})+\b")
NO_ITEM = re.compile(r"(?i)total|subtotal|pagad|pagar|efectivo|tarjeta|transf|cr[eé]dito|cambio|descuento|propina|domicil|valor:|nequi|daviplata")
def items(t):
    """Prices of the item rows: lines between the table header and SUBTOTAL that end in a thousands-formatted price."""
    m = re.search(r"(?is)descrip\w*.*?\n(.*?)(?:sub\s*total|\*\*total)", t or "")
    return Counter(re.sub(r"[.,]", "", p[-1]) for l in (m.group(1).splitlines() if m else []) if not NO_ITEM.search(l) and (p := PRECIO.findall(l)))
def nit(t):
    m = re.search(r"(?i)n\s*[i1l]\s*t\W{0,3}([\d][\d .\-]{5,})", t or ""); return re.sub(r"\D", "", m.group(1)) if m else ""
leidos = {str(d.get("numero")): d for docs in hechas.values() for d in docs if d.get("tipo") == "venta"}
nit_ok = nit_n = it_ref = it_hit = it_got = 0
for r in ref["documentos"]:
    got = leidos.get(r["numero"]); et = r["documento"].get("texto") or ""
    if got is None: continue
    if nit(et): nit_n += 1; nit_ok += nit(got.get("texto")) == nit(et)
    if "escrip" in et:
        a, b = items(et), items(got.get("texto")); it_ref += sum(a.values()); it_got += sum(b.values()); it_hit += sum((a & b).values())

T = [json.loads(l) for l in tiempos_p.read_text(encoding="utf-8").splitlines()]
res = {"motor": motor, **{k: inf[k] for k in ("total", "leidos", "omitidos", "omitidos_numeros", "por_causa", "dudosos", "validados_con_error",
       "validados_con_error_numeros", "errores_lectura")}, "por_campo": inf["por_campo"],
       "nit": {"ok": nit_ok, "de": nit_n}, "items": {"ref": it_ref, "leidos": it_got, "aciertos": it_hit},
       "tiempo": {"fotos": len(T), "trozos": sum(t["trozos"] for t in T), "ocr_s_por_foto": round(sum(t["ocr_s"] for t in T) / len(T), 2),
                  "total_s_por_foto": round(sum(t["ocr_s"] + t["prep_s"] for t in T) / len(T), 2)},
       "pico_ram_mb": {"motor": mem_engine, "proceso_python": round(mem(K.GetCurrentProcess()), 1)}}
if base.startswith("indra"): res["indra_carga_s"] = eng.load["load_s"]
(RES / f"resultado_{motor}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
(RES / f"medir_{motor}.json").write_text(json.dumps(inf, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
av.unlink(missing_ok=True)
print(json.dumps({k: v for k, v in res.items() if k not in ("omitidos_numeros", "validados_con_error_numeros")}, ensure_ascii=False))
