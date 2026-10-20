"""Trabajador Indra OCR (ADR-016). Corre en el venv 3.14 aislado (`python -I`), NO en el proceso de la app.

Protocolo: JSON por líneas en stdin/stdout.
  salida inicial   {"ready": true, "version": "1.1.2", "load_s": float}
  {"op":"numeros","png":b64}  -> {"texto": str, "ms": float}
  {"op":"upright","png":b64}  -> {"giro": 0|90|180|270, "incl": float, "ms": float}   (giro horario que endereza; incl en grados, signo de PIL.rotate)
  {"op":"quit"}               -> {"bye": true} y sale
  cualquier error             -> {"error": str}
EOF en stdin también cierra. Hilos: INDRA_HILOS (4 por defecto)."""
import os
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
import base64, json, sys, time


def filas(lines):
    """Cajas que comparten fila (solape vertical >= 50 % de la menor) -> una línea de texto, izquierda a derecha, unidas por ' | '."""
    bs = sorted(lines, key=lambda l: (l[0][1] + l[0][3]) / 2)
    out = []
    for b in bs:
        y0, y1 = b[0][1], b[0][3]
        for row in out:
            r0, r1 = row["y"]
            if min(y1, r1) - max(y0, r0) >= 0.5 * min(y1 - y0, r1 - r0):
                row["b"].append(b); row["y"] = (min(r0, y0), max(r1, y1)); break
        else:
            out.append({"y": (y0, y1), "b": [b]})
    out.sort(key=lambda r: r["y"][0])
    return "\n".join(" | ".join(t for _, t, _ in sorted(r["b"], key=lambda l: l[0][0])) for r in out)


def responder(obj):
    sys.stdout.write(json.dumps(obj, default=float) + "\n"); sys.stdout.flush()


def main():
    import cv2, numpy as np
    import indra_ocr
    try:
        hilos = max(1, int(os.environ.get("INDRA_HILOS", "4")))
    except ValueError:
        hilos = 4
    t0 = time.perf_counter()
    carpeta = os.environ.get("INDRA_OCR_MODEL_DIR") or indra_ocr.model_dir()
    ocr = indra_ocr.OrtOCR(carpeta, threads=hilos)
    try:
        from importlib.metadata import version
        ver = version("indra-ocr")
    except Exception:
        ver = "1.1.2"
    responder({"ready": True, "version": ver, "load_s": round(time.perf_counter() - t0, 2)})

    for raw in sys.stdin:
        if not raw.strip():
            continue
        try:
            req = json.loads(raw)
            op = req.get("op")
            if op == "quit":
                responder({"bye": True}); return
            t = time.perf_counter()
            gris = cv2.imdecode(np.frombuffer(base64.b64decode(req["png"]), np.uint8), cv2.IMREAD_GRAYSCALE)
            if gris is None:
                raise ValueError("png ilegible")
            if op == "numeros":
                page = ocr(gris, turn=False)   # la app ya enderezó la hoja
                texto = filas([[ln.box, ln.text, ln.conf] for ln in page.lines])
                responder({"texto": texto, "ms": round(1000 * (time.perf_counter() - t), 1)})
            elif op == "upright":
                _, k, a = ocr.upright(gris)    # k: 0..3 giros horarios; 4 = columnas verticales (= 270 horario)
                giro = 270 if k == 4 else 90 * int(k)
                responder({"giro": giro, "incl": round(float(a), 2), "ms": round(1000 * (time.perf_counter() - t), 1)})
            else:
                raise ValueError(f"op desconocida: {op!r}")
        except Exception as e:   # un pedido malo no mata al trabajador
            responder({"error": f"{type(e).__name__}: {e}"})


if __name__ == "__main__":
    main()
