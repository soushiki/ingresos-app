"""T9 · archivos de ataque del modo contador web (S2, S4). Los usan probar_web.py (lado Python) y la checklist en navegador
(CHECKLIST.md). Se arman en memoria: el de 25 MB no va al repo y en Windows un nombre con `<script>` no puede existir en
disco, así que la página lo prueba con un `File` armado en la consola (CHECKLIST.md).
`python web/pruebas/ataques/ataques.py <carpeta>` los escribe para elegirlos a mano en el selector."""
import json, sys
from pathlib import Path

MB = 2 ** 20
NOMBRE_SCRIPT = '<script>alert("x")</script><img src=x onerror=alert(1)>.json'


def _exe() -> bytes:
    "Cabecera MZ/PE de mentira (no ejecuta nada): lo que el navegador ve si alguien renombra un .exe a .json."
    dos = bytearray(b"MZ" + b"\x90\x00" + b"\x00" * 56)
    dos[0x3C:0x40] = (0x80).to_bytes(4, "little")
    cuerpo = b"This program cannot be run in DOS mode.\r\r\n$".ljust(0x80 - len(dos), b"\x00")
    return bytes(dos) + cuerpo + b"PE\x00\x00" + bytes(range(256)) * 8


# nombre del archivo → (bytes, lo que dice libro.generar, lo que dice la página). Ninguno debe ejecutar nada ni colgar la página.
# El anidado lo corta antes el Worker (en Pyodide json.loads desbordaría la pila de JS) y el de 25 MB, app.js antes de leerlo.
CASOS = {
    "no_es_crudo.json": (json.dumps({"name": "mi-proyecto", "version": "1.0.0", "dependencies": {}}).encode(),
                         "no es de datos crudos de Ingresos", "no es de datos crudos de Ingresos"),
    "exe_renombrado.json": (_exe(), "no es un .json válido", "no es un .json válido"),
    "anidado.json": (b"[" * 100_000 + b"]" * 100_000, "no es un .json válido", "demasiado anidado"),
    "gigante_25mb.json": (b" " * (25 * MB), "más de 20 MB", "más de 20 MB"),
}


if __name__ == "__main__":
    destino = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    destino.mkdir(parents=True, exist_ok=True)
    for nombre, (datos, *_) in CASOS.items():
        (destino / nombre).write_bytes(datos)
        print(f"{nombre}: {len(datos):,} bytes")
