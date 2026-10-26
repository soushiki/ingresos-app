"""Spike T1: sirve la página mínima con las cabeceras exactas de `_headers` (formato Netlify).

    python servir.py --pyodide <carpeta con pyodide.mjs> --wheels <carpeta con .whl> [--puerto 5071]

Rutas: /pyodide/314.0.7/* → --pyodide, /py/* → --wheels, el resto → esta carpeta.
Solo 127.0.0.1. Los MIME se fijan a mano (.mjs, .wasm) para no depender del registro de Windows.
"""
import argparse
import http.server
from pathlib import Path

AQUI = Path(__file__).resolve().parent
MIME = {".html": "text/html; charset=utf-8", ".js": "text/javascript", ".mjs": "text/javascript",
        ".wasm": "application/wasm", ".json": "application/json", ".zip": "application/zip",
        ".whl": "application/zip", ".css": "text/css", ".map": "application/json"}


def leer_headers(ruta):
    """Solo el bloque `/*`, como lo aplica Netlify a todo el sitio."""
    cab, dentro = [], False
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        if not linea.strip():
            continue
        if not linea[0].isspace():
            dentro = linea.strip() == "/*"
        elif dentro:
            nombre, _, valor = linea.strip().partition(":")
            cab.append((nombre.strip(), valor.strip()))
    return cab


def manejador(pyodide, wheels, cabeceras):
    raices = [("/pyodide/314.0.7/", pyodide), ("/py/", wheels), ("/", AQUI)]

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            url = self.path.split("?", 1)[0]
            if url == "/":
                url = "/index.html"
            for pref, raiz in raices:
                if url.startswith(pref):
                    f = (raiz / url[len(pref):]).resolve()
                    break
            if not f.is_relative_to(raiz) or not f.is_file() or f.name in ("servir.py", "_headers"):
                return self.responder(404, b"no existe", "text/plain")
            self.responder(200, f.read_bytes(), MIME.get(f.suffix, "application/octet-stream"))

        def responder(self, codigo, cuerpo, tipo):
            self.send_response(codigo)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(cuerpo)))
            self.send_header("Cache-Control", "no-store")
            for n, v in cabeceras:
                self.send_header(n, v)
            self.end_headers()
            self.wfile.write(cuerpo)

    return H


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--pyodide", required=True, type=Path)
    a.add_argument("--wheels", required=True, type=Path)
    a.add_argument("--puerto", type=int, default=5071)
    o = a.parse_args()
    h = manejador(o.pyodide.resolve(), o.wheels.resolve(), leer_headers(AQUI / "_headers"))
    print(f"spike CSP en http://127.0.0.1:{o.puerto}/")
    http.server.ThreadingHTTPServer(("127.0.0.1", o.puerto), h).serve_forever()
