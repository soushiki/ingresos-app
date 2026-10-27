"""T4 · arma web/dist/ del modo contador web (ADR-027, ADR-028, S1, S4, S5).

    python herramientas/web_build.py [--version X.Y.Z] [--publicar]

- Baja Pyodide y los wheels de web/web.lock a web/cache/ (una vez) y verifica su sha256 en cada build.
- nucleo.zip = solo la lista blanca (ADR-028), con los dos __init__.py vacíos y bytes deterministas (mismo código → mismo zip).
- web/dist/ = /pyodide/<ver>/ + /py/ (compartidos) + /vX.Y.Z/ (núcleo, manifiesto y web/src) + índice raíz + _headers (CSP de S4).
- T10: cada web/publicadas/vX.Y.Z/ viaja tal cual a dist/ si coincide byte a byte con web/publicadas.lock; --publicar congela
  la versión recién armada (copia + sha256 al lock) y se niega si ya estaba publicada.
Falla (BuildError) si entra un archivo prohibido, una URL remota o ejecución dinámica en el código propio, o un sha256 distinto."""
from __future__ import annotations
import argparse, hashlib, html, io, json, re, shutil, sys, tarfile, urllib.request, zipfile
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
WEB = APP / "web"
LOCK, CACHE, DIST, SRC = WEB / "web.lock", WEB / "cache", WEB / "dist", WEB / "src"
PUB, PLOCK = WEB / "publicadas", WEB / "publicadas.lock"   # ADR-027: versiones congeladas, en git

# S4 (02-requirements), probada en Chrome/Edge en el spike T1: no se toca sin pasar otra vez por ADR-028.
CSP = ("default-src 'none'; script-src 'self' 'wasm-unsafe-eval'; worker-src 'self' blob:; connect-src 'self'; "
       "img-src 'self' blob: data:; style-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
INMUTABLE = "public, max-age=31536000, immutable"

# ADR-028: lo que `libro.generar` importa y los JSON que esos módulos leen al importarse (03 §4). Nada más.
LISTA_BLANCA = [
    "parser_module/__init__.py",
    "parser_module/numeros.py",
    "parser_module/contable/__init__.py",
    "parser_module/contable/libro.py",
    "parser_module/contable/asientos.py",
    "parser_module/contable/documentos.py",
    "parser_module/contable/exportar.py",
    "parser_module/contable/extracto.py",
    "parser_module/contable/puc.py",
    "parser_module/contable/puc_cuentas.json",
    "parser_module/contable/plan_de_cuentas.json",
    "parser_module/contable/normalizacion.json",
    "parser_module/contable/extracto_reglas.json",
    "parser_module/contable/por_confirmar.json",
]
# Los reales importan el clasificador (Motor, terceros) y el parser OCR: en el zip van vacíos.
VACIOS = {"parser_module/__init__.py", "parser_module/contable/__init__.py"}
# S1: personas, datos del negocio, modelo de clasificación, config local. Ninguno puede llegar al sitio.
PROHIBIDO = re.compile(r"(^|/)(terceros_cuentas[^/]*\.json|modelo_manual\.json|libro[^/]*\.json|contable\.json|[^/]*\.db|datos/.*|\.env)$", re.I)
# ADR-028 / S3: salidas y ejecución dinámica en el código propio (no en Pyodide, que trae URLs de su CDN por defecto).
SALIDA = re.compile(r"https?://|micropip|innerHTML|\beval\s*\(|new\s+Function")
CODIGO = {".py", ".js", ".mjs", ".html", ".css"}


class BuildError(Exception):
    "El build se niega: el mensaje dice qué regla (ADR/S) y qué archivo."


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def leer_lock(ruta: Path = LOCK) -> dict:
    return json.loads(ruta.read_text(encoding="utf8"))


def dependencias(lock: dict) -> list[dict]:
    return [lock["pyodide"], *lock["wheels"]]


def bajar(lock: dict, cache: Path = CACHE) -> dict[str, Path]:
    """S5: cada dependencia queda en `cache` y coincide con su sha256. Si un archivo ya bajado no coincide no se reemplaza
    en silencio (puede ser una alteración): el build para y el usuario lo borra a mano."""
    cache.mkdir(parents=True, exist_ok=True)
    rutas = {}
    for d in dependencias(lock):
        f = cache / d["archivo"]
        if not f.exists():
            print(f"  bajando {d['archivo']}…", flush=True)
            with urllib.request.urlopen(d["url"], timeout=120) as r:
                datos = r.read()
            if sha256(datos) != d["sha256"]:
                raise BuildError(f"S5: {d['archivo']} bajado de {d['url']} no coincide con el sha256 de web.lock; no se guarda")
            f.with_suffix(".part").write_bytes(datos)
            f.with_suffix(".part").replace(f)
        if sha256(f.read_bytes()) != d["sha256"]:
            raise BuildError(f"S5: sha256 distinto en web/cache/{d['archivo']}; bórrelo para bajarlo de nuevo (y revise por qué cambió)")
        rutas[d["archivo"]] = f
    return rutas


def revisar_nombre(nombre: str) -> None:
    if PROHIBIDO.search(nombre.replace("\\", "/")):
        raise BuildError(f"ADR-028/S1: archivo prohibido en el paquete: {nombre}")


def revisar_codigo(nombre: str, texto: str) -> None:
    m = SALIDA.search(texto)
    if m:
        linea = texto.count("\n", 0, m.start()) + 1
        raise BuildError(f"ADR-028: salida o ejecución no permitida en {nombre}:{linea} («{m.group(0)}»)")


def nucleo_zip(raiz: Path = APP, lista: list[str] = LISTA_BLANCA) -> bytes:
    "ADR-028: el núcleo por lista blanca. Fecha fija y orden fijo → mismos bytes para el mismo código (publicadas.lock, T10)."
    for n in lista:
        revisar_nombre(n)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for n in sorted(lista):
            datos = b"" if n in VACIOS else (raiz / n).read_bytes()
            if n.endswith(".py"):
                revisar_codigo(n, datos.decode("utf8"))
            zi = zipfile.ZipInfo(n, date_time=(1980, 1, 1, 0, 0, 0))
            zi.compress_type, zi.external_attr = zipfile.ZIP_DEFLATED, 0o644 << 16
            z.writestr(zi, datos)
    return buf.getvalue()


def cabeceras(lock: dict, versiones: list[str]) -> str:
    """S4 + ADR-027. Netlify junta las reglas que coinciden con una ruta, así que Cache-Control va solo en las rutas
    versionadas (la raíz queda con la caché corta por defecto de Netlify)."""
    out = ["/*", f"  Content-Security-Policy: {CSP}", "  X-Content-Type-Options: nosniff",
           "  Referrer-Policy: no-referrer", "  Permissions-Policy:", ""]
    for ruta in [f"/pyodide/{lock['pyodide']['version']}/*", "/py/*", *(f"/v{v}/*" for v in versiones)]:
        out += [ruta, f"  Cache-Control: {INMUTABLE}", ""]
    return "\n".join(out)


def indice(versiones: list[str]) -> str:
    "Raíz: lista de versiones, la última arriba. Sin script ni estilo en línea (CSP)."
    filas = "\n".join(f'    <li><a href="v{html.escape(v)}/">v{html.escape(v)}</a></li>' for v in versiones)
    return ("<!doctype html>\n<html lang=\"es\">\n<head>\n  <meta charset=\"utf-8\">\n"
            "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
            "  <title>Libro contable · contador</title>\n</head>\n<body>\n  <h1>Libro contable · versiones</h1>\n"
            f"  <ul>\n{filas}\n  </ul>\n</body>\n</html>\n")


def _clave(v: str) -> tuple:
    return tuple(int(x) for x in v.split("."))


def leer_publicadas(plock: Path = PLOCK) -> dict[str, dict[str, str]]:
    "versión → {ruta dentro de /vX.Y.Z/ → sha256}. Sin lock = nada publicado todavía."
    return json.loads(plock.read_text(encoding="utf8"))["versiones"] if plock.exists() else {}


def _archivos(carpeta: Path) -> dict[str, bytes]:
    return {p.relative_to(carpeta).as_posix(): p.read_bytes() for p in sorted(carpeta.rglob("*")) if p.is_file()}


def verificar_publicadas(pub: Path = PUB, plock: Path = PLOCK, lock: dict | None = None) -> dict[str, dict[str, bytes]]:
    """ADR-027: cada carpeta publicada = su entrada del lock, archivo por archivo (ni uno de más, de menos ni cambiado), y
    web.lock todavía trae el Pyodide y los wheels que su manifiesto pide. Devuelve versión → {ruta → bytes}."""
    lock = lock or leer_lock()
    registro = leer_publicadas(plock)
    carpetas = {p.name[1:] for p in pub.iterdir() if p.is_dir()} if pub.is_dir() else set()
    for v in sorted(carpetas - set(registro), key=_clave):
        raise BuildError(f"ADR-027: web/publicadas/v{v}/ no está en publicadas.lock; publique con --publicar, no a mano")
    out = {}
    for v, esperado in sorted(registro.items(), key=lambda kv: _clave(kv[0])):
        hay = _archivos(pub / f"v{v}") if (pub / f"v{v}").is_dir() else {}
        distintos = sorted(r for r in set(esperado) | set(hay) if r not in hay or sha256(hay[r]) != esperado.get(r))
        if distintos:
            raise BuildError(f"ADR-027: la versión publicada v{v} cambió ({', '.join(distintos[:3])}); publique un tag nuevo")
        man = json.loads(hay["manifiesto.json"])
        faltan = [w for w in man["wheels"] if w not in {x["archivo"] for x in lock["wheels"]}]
        if man["pyodide"] != lock["pyodide"]["version"] or faltan:
            raise BuildError(f"ADR-027: v{v} necesita Pyodide {man['pyodide']} y {man['wheels']}, que web.lock ya no trae")
        out[v] = hay
    return out


def publicar(version: str, dist: Path = DIST, pub: Path = PUB, plock: Path = PLOCK) -> dict[str, str]:
    "ADR-027: congela dist/vX.Y.Z/ en web/publicadas/ y suma su sha256 al lock. Una versión se publica una sola vez."
    registro = leer_publicadas(plock)
    if version in registro or (pub / f"v{version}").exists():
        raise BuildError(f"ADR-027: v{version} ya está publicada; publique un tag nuevo")
    origen = dist / f"v{version}"
    if not (origen / "manifiesto.json").is_file():
        raise BuildError(f"ADR-027: no hay {origen} armada; corra el build de v{version} primero")
    archivos = _archivos(origen)
    for rel, datos in archivos.items():
        (pub / f"v{version}" / rel).parent.mkdir(parents=True, exist_ok=True)
        (pub / f"v{version}" / rel).write_bytes(datos)
    registro[version] = {rel: sha256(d) for rel, d in archivos.items()}
    nota = "ADR-027: sha256 de cada archivo de web/publicadas/vX.Y.Z/. Lo escribe web_build.py --publicar; nunca a mano."
    plock.write_text(json.dumps({"nota": nota, "versiones": dict(sorted(registro.items(), key=lambda kv: _clave(kv[0])))},
                                ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    return registro[version]


def armar(version: str, dist: Path = DIST, cache: Path = CACHE, src: Path = SRC, lock: dict | None = None,
          lista: list[str] = LISTA_BLANCA, pub: Path = PUB, plock: Path = PLOCK) -> dict:
    """Arma `dist` desde cero: las versiones publicadas tal cual y `version` desde web/src (o su copia publicada, si ya lo
    está: una versión publicada no se vuelve a armar). Devuelve un resumen (rutas → sha256) para el informe y los tests."""
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise BuildError(f"ADR-027: versión «{version}» no es X.Y.Z")
    lock = lock or leer_lock()
    rutas = bajar(lock, cache)
    publicadas = verificar_publicadas(pub, plock, lock)
    py = lock["pyodide"]

    propios = {}   # ruta en dist → bytes, todo lo que no es Pyodide/wheels (se revisa entero)
    for v, archivos in publicadas.items():
        propios.update({f"v{v}/{rel}": d for rel, d in archivos.items()})
    if version in publicadas:
        manifiesto = json.loads(publicadas[version]["manifiesto.json"])
    else:
        manifiesto = _version_nueva(version, src, lock, lista, propios)
    versiones = sorted(set(publicadas) | {version}, key=_clave, reverse=True)
    propios["index.html"] = indice(versiones).encode("utf8")
    propios["_headers"] = cabeceras(lock, versiones).encode("utf8")

    if dist.exists():
        shutil.rmtree(dist)
    for rel, datos in propios.items():
        (dist / rel).parent.mkdir(parents=True, exist_ok=True)
        (dist / rel).write_bytes(datos)
    destino = dist / "pyodide" / py["version"]
    destino.mkdir(parents=True)
    with tarfile.open(rutas[py["archivo"]], "r:gz") as t:
        for n in py["servir"]:   # solo los que carga el navegador: sin consolas html, mapas ni .d.ts
            (destino / n).write_bytes(t.extractfile(f"package/{n}").read())
    (dist / "py").mkdir()
    for w in lock["wheels"]:
        shutil.copyfile(rutas[w["archivo"]], dist / "py" / w["archivo"])
    return {"version": version, "manifiesto": manifiesto, "versiones": versiones, "publicada": version in publicadas,
            "archivos": {p.relative_to(dist).as_posix(): sha256(p.read_bytes()) for p in sorted(dist.rglob("*")) if p.is_file()}}


def _version_nueva(version: str, src: Path, lock: dict, lista: list[str], propios: dict[str, bytes]) -> dict:
    "Núcleo + manifiesto + web/src de una versión sin publicar, a `propios`. Devuelve el manifiesto."
    nucleo = nucleo_zip(APP, lista)
    if src.is_dir():
        for f in sorted(p for p in src.rglob("*") if p.is_file()):
            rel = f.relative_to(src).as_posix()
            revisar_nombre(rel)
            datos = f.read_bytes()
            if f.suffix in CODIGO:
                revisar_codigo(f"web/src/{rel}", datos.decode("utf8"))
            propios[f"v{version}/{rel}"] = datos
    manifiesto = {"version": version, "pyodide": lock["pyodide"]["version"], "wheels": [w["archivo"] for w in lock["wheels"]],
                  "nucleo_sha256": sha256(nucleo)}
    propios[f"v{version}/nucleo.zip"] = nucleo
    propios[f"v{version}/manifiesto.json"] = (json.dumps(manifiesto, ensure_ascii=False, indent=2) + "\n").encode("utf8")
    return manifiesto


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--version", default=(APP / "VERSION").read_text(encoding="utf8").strip())
    a.add_argument("--publicar", action="store_true", help="congela la versión armada en web/publicadas/ (ADR-027)")
    o = a.parse_args()
    try:
        r = armar(o.version)
        if o.publicar:
            if r["publicada"]:
                raise BuildError(f"ADR-027: v{o.version} ya está publicada; publique un tag nuevo")
            n = publicar(o.version)
            print(f"✓ v{o.version} publicada: {len(n)} archivos en web/publicadas/v{o.version}/ y publicadas.lock")
    except BuildError as e:
        print(f"✗ build detenido: {e}")
        return 1
    total = sum((DIST / p).stat().st_size for p in r["archivos"])
    nota = " (copia publicada; web/src no se usa)" if r["publicada"] else ""
    print(f"✓ web/dist/ v{r['version']}{nota}: {len(r['archivos'])} archivos, {total / 2**20:.1f} MB; "
          f"versiones {', '.join(r['versiones'])}; nucleo.zip {r['manifiesto']['nucleo_sha256'][:12]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
