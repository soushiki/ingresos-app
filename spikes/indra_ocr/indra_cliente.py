"""Project-side client for indra_worker.py (which lives in the isolated venv) + text layouts for the project's parser."""
import base64, io, json, os, subprocess
from pathlib import Path

AQUI = Path(__file__).resolve().parent
VENV_PY = Path(os.environ.get("INDRA_VENV", AQUI / "indra_venv")) / "Scripts" / "python.exe"   # isolated venv, not the project one


class Indra:
    name = model = "indra-ocr-1.1.2"

    def __init__(self, threads=4, layout="filas"):
        env = dict(os.environ, HF_HUB_DISABLE_TELEMETRY="1", PYTHONIOENCODING="utf-8")
        self.p = subprocess.Popen([str(VENV_PY), "-I", str(AQUI / "indra_worker.py"), str(threads)], stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, text=True, encoding="utf-8", env=env, cwd=str(AQUI.parent))
        self.load = json.loads(self.p.stdout.readline())
        self.layout, self.ms = layout, []

    def leer(self, img):
        """PIL image -> worker response."""
        b = io.BytesIO(); img.save(b, "PNG")
        self.p.stdin.write(json.dumps({"png": base64.b64encode(b.getvalue()).decode()}) + "\n"); self.p.stdin.flush()
        r = json.loads(self.p.stdout.readline()); self.ms.append(r["ms"]); return r

    def upright(self, img):
        """PIL image -> (PIL image turned upright and straightened by Indra, quarter turns k, skew degrees)."""
        from PIL import Image
        b = io.BytesIO(); img.save(b, "PNG")
        self.p.stdin.write(json.dumps({"png": base64.b64encode(b.getvalue()).decode(), "upright": True}) + "\n"); self.p.stdin.flush()
        r = json.loads(self.p.stdout.readline())
        return Image.open(io.BytesIO(base64.b64decode(r["png"]))).convert("RGB"), r["k"], r["skew"], r["ms"]

    def texto(self, img):
        r = self.leer(img)
        return filas(r["lines"]) if self.layout == "filas" else "\n".join(t for _, t, _ in r["lines"])

    def cerrar(self):
        self.p.stdin.write('{"quit": true}\n'); self.p.stdin.flush()
        r = json.loads(self.p.stdout.readline()); self.p.wait(); return r


def filas(lines):
    """Boxes that share a row (vertical overlap ≥ 50 % of the shorter box) -> one text line, left to right, joined by ' | '.
    Indra returns each column of a receipt row (plate · qty · price) as its own line; the parser expects one row per line."""
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
