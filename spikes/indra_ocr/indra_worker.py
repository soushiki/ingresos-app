"""Runs inside the isolated indra venv. One JSON request per stdin line: {"png": <base64>} -> {"lines", "markdown", "ms"}.
{"quit": true} -> {"peak_rss_mb"} and exit. Keeps the model loaded between requests."""
import base64, ctypes, json, sys, time
from ctypes import wintypes
import cv2, numpy as np
import indra_ocr


def peak_mb():
    class PMC(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t), ("a", ctypes.c_size_t), ("b", ctypes.c_size_t), ("c", ctypes.c_size_t),
                    ("d", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
    p = PMC(); p.cb = ctypes.sizeof(PMC)
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.GetCurrentProcess.restype = wintypes.HANDLE
    k.K32GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
    k.K32GetProcessMemoryInfo(k.GetCurrentProcess(), ctypes.byref(p), p.cb)
    return p.PeakWorkingSetSize / 2**20


threads = int(sys.argv[1]) if len(sys.argv) > 1 else 4
t0 = time.perf_counter()
ocr = indra_ocr.OrtOCR(indra_ocr.model_dir(), threads=threads)
print(json.dumps({"ready": True, "load_s": round(time.perf_counter() - t0, 2)}), flush=True)
for raw in sys.stdin:
    req = json.loads(raw)
    if req.get("quit"):
        print(json.dumps({"peak_rss_mb": round(peak_mb(), 1)}), flush=True); break
    gray = cv2.imdecode(np.frombuffer(base64.b64decode(req["png"]), np.uint8), cv2.IMREAD_GRAYSCALE)
    t = time.perf_counter()
    if req.get("upright"):                 # orientation test: the page turned (orient.onnx) and straightened (estimate_skew)
        img = cv2.imdecode(np.frombuffer(base64.b64decode(req["png"]), np.uint8), cv2.IMREAD_COLOR)
        _, k, a = ocr.upright(gray)
        if k: img = np.ascontiguousarray(np.rot90(img, 1 if k == 4 else -k))   # 4 = vertical columns (as OrtOCR._turn)
        if abs(a) >= 0.3:
            h, w = img.shape[:2]
            img = cv2.warpAffine(img, cv2.getRotationMatrix2D((w / 2, h / 2), a, 1.0), (w, h), borderMode=cv2.BORDER_REPLICATE)
        print(json.dumps({"png": base64.b64encode(cv2.imencode(".png", img)[1].tobytes()).decode(), "k": k, "skew": a,
                          "ms": round(1000 * (time.perf_counter() - t), 1)}), flush=True)
        continue
    page = ocr(gray, turn=False)          # the project already turned the page upright (orientacion.preparar_pagina)
    print(json.dumps({"lines": [[ln.box, ln.text, ln.conf] for ln in page.lines], "markdown": page.markdown,
                      "ms": round(1000 * (time.perf_counter() - t), 1)}, default=float), flush=True)
