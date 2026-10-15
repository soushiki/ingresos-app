"""Uso:  python -m ocr_module.cli fotos/ -o salida/   (desde la carpeta que contiene ocr_module/)"""
import argparse, json, sys
from pathlib import Path
try:
    from dotenv import load_dotenv; load_dotenv()
except ImportError:
    pass
from . import collect_images, digitize_many, get_engine


def main():
    ap = argparse.ArgumentParser(description="Imágenes → texto plano")
    ap.add_argument("inputs", nargs="+", help="imágenes y/o carpetas")
    ap.add_argument("-o", "--out", default="ocr_out")
    ap.add_argument("--engine", default="local", choices=["local", "tesseract", "gemini"])
    ap.add_argument("--model", default=None, help="p. ej. qwen2.5vl:7b, qwen3-vl:8b (local) o gemini-2.5-flash")
    ap.add_argument("--workers", type=int, default=None, help="por defecto 1 en local, 4 en nube")
    ap.add_argument("--raw", action="store_true", help="enviar la imagen sin preprocesar")
    a = ap.parse_args()
    imgs = collect_images(*a.inputs)
    if not imgs:
        sys.exit("No encontré imágenes soportadas.")
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    eng = get_engine(a.engine, **({"model": a.model} if a.model and a.engine != "tesseract" else {}))
    workers = a.workers or (4 if a.engine == "gemini" else 1)
    res = digitize_many(imgs, eng, workers, not a.raw,
                        lambda d, n, r: print(f"[{d}/{n}] {'OK ' if r.ok else 'ERR'} {r.source} ({r.seconds}s) {r.error}"))
    with open(out / "resultados.jsonl", "w", encoding="utf8") as f:
        for r in res:
            f.write(json.dumps(r.to_dict(), ensure_ascii=False) + "\n")
            if r.ok:
                (out / (Path(r.source).stem + ".txt")).write_text(r.text, encoding="utf8")
    bad = sum(not r.ok for r in res)
    print(f"\nListo: {len(res) - bad} leídas, {bad} con error → {out.resolve()}")


if __name__ == "__main__":
    main()
