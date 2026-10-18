"""Spike 2d (01d-fuentes-ocr.md): Google Vision DOCUMENT_TEXT_DETECTION contra la referencia, en las 20 fotos con más dudosos.
Nunca escribe libro.json. Tres pasos, cada uno se puede repetir:
    python spikes/spike_google_vision.py preparar --fotos "D:/.../SEPTIEMBRE"   # recortes tapados + hoja de contacto (sin red)
    python spikes/spike_google_vision.py enviar   [--max 150]                   # solo los recortes «ok» sin respuesta guardada
    python spikes/spike_google_vision.py medir    --fotos "D:/.../SEPTIEMBRE"   # informe «google» y «google_filas»
Privacidad: se tapan (blanco, a todo lo ancho) las líneas de la dirección, el teléfono, el NIT y la identificación del cliente, y «<NOMBRE>» si aparece. Un recorte
donde no se halla nada que tapar ni el «RECIBO #» queda «revisar» y no se envía hasta marcarlo a mano en el manifiesto."""
import argparse, base64, difflib, io, json, os, re, sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent   # spikes/ cuelga de la raíz del proyecto
sys.path.insert(0, str(BASE))
DATOS = BASE / "datos"
CARPETA = DATOS / "referencia" / "google"
MANIFIESTO = CARPETA / "manifiesto.json"
URL = "https://vision.googleapis.com/v1/images:annotate"
try: from dotenv import load_dotenv; load_dotenv(BASE / ".env")
except ImportError: pass
# Nombre del local y número de su dirección: fuera del repo (público), en .env. NOMBRE_LOCAL tapa solo la palabra
# (sale también en platos: «THE BIG <NOMBRE> BURGER»); DIRECCION_LOCAL es una regex extra, p. ej. 12\s*-\s*34.
NOMBRE = tuple(w.strip().upper() for w in os.environ.get("NOMBRE_LOCAL", "").split(",") if w.strip())
if not NOMBRE: sys.exit("Falta NOMBRE_LOCAL en .env (palabra del nombre del local que se tapa)")
PRIVADO = ("TELEFONOS", "TELEFONO", "6434897")        # la línea entera
DIRECCION = re.compile(r"\bCRA\b|\bCARRERA\b|\bN[I1L]T\b|IDENTIFICAC|\bC\.?C\.?\s*[:#]"   # + NIT y cédulas
                       + (f"|{os.environ['DIRECCION_LOCAL']}" if os.environ.get("DIRECCION_LOCAL") else ""))


def _clave() -> str:
    f = Path.home() / ".claves" / "google_vision_key.txt"
    k = f.read_text(encoding="utf-8-sig").strip() if f.exists() else os.environ.get("GOOGLE_VISION_KEY", "").strip()
    if not k: sys.exit("Falta la clave: ~/.claves/google_vision_key.txt o GOOGLE_VISION_KEY")
    return k


def _privada(palabra: str, lista=PRIVADO) -> bool:
    p = re.sub(r"[^A-Z0-9]", "", palabra.upper().replace("Ó", "O"))
    if len(p) < 4: return False
    p0 = p.replace("0", "O")
    return any(difflib.SequenceMatcher(None, p0 if not w.isdigit() else p, w).ratio() >= 0.75 for w in lista)


def _lineas(img):
    """Líneas de Tesseract sobre el recorte ×3: [(texto, (x0, y0, x1, y1), [(palabra, caja)…])] en coordenadas del recorte."""
    import pytesseract
    g = img.convert("L").resize((img.width * 3, img.height * 3))
    d = pytesseract.image_to_data(g, lang="spa", config="--psm 6", output_type=pytesseract.Output.DICT)
    por = {}
    for i, t in enumerate(d["text"]):
        if not t.strip(): continue
        k = (d["block_num"][i], d["par_num"][i], d["line_num"][i]); x, y, w, h = (d[c][i] // 3 for c in ("left", "top", "width", "height"))
        a = por.setdefault(k, [[], [x, y, x + w, y + h], []]); a[0].append(t); a[2].append((t, (x, y, x + w, y + h)))
        b = a[1]; b[0], b[1], b[2], b[3] = min(b[0], x), min(b[1], y), max(b[2], x + w), max(b[3], y + h)
    return [(" ".join(ws), tuple(b), pal) for ws, b, pal in sorted(por.values(), key=lambda v: v[1][1])]


def tapar(img):
    """→ (imagen tapada, estado, líneas tapadas). estado: «ok» o «revisar»."""
    from PIL import ImageDraw
    img = img.copy(); dib = ImageDraw.Draw(img); lineas = _lineas(img); tapadas = []
    # el número y la fecha no se tocan: la franja se recorta para no pisar esas líneas
    protegidas = [b for t, b, _ in lineas if re.search(r"RECIB|FECHA|ORIGINAL|PROPIETARIO|MESA", t.upper())]
    altos = sorted(b[3] - b[1] for _, b, _ in lineas) or [12]; tope = 1.6 * altos[len(altos) // 2]
    for texto, (x0, y0, x1, y1), pal in lineas:
        for w, (a0, b0, a1, b1) in pal:
            if _privada(w, NOMBRE): dib.rectangle((a0 - 2, b0 - 2, a1 + 2, b1 + 2), fill="white"); tapadas.append(w)
        if protegidas and any(b[1] == y0 and b[3] == y1 for b in protegidas): continue
        if DIRECCION.search(texto.upper()) or any(_privada(w) for w in texto.split()):
            c = (y0 + y1) / 2; a, z = max(0, y0 - 2, c - tope / 2), min(y1 + 2, c + tope / 2)
            for _, p0, _, p1 in protegidas:
                if p0 <= c <= p1: continue
                if p1 < c: a = max(a, p1 + 1)
                elif p0 > c: z = min(z, p0 - 1)
            dib.rectangle((0, a, img.width, z), fill="white"); tapadas.append(texto)
        elif re.search(r"\d{7,}", texto.replace(" ", "")) and "$" not in texto and "TOTAL" not in texto.upper():
            dib.rectangle((0, max(0, y0 - 2), img.width, y1 + 2), fill="white"); tapadas.append(texto)   # NIT/cédula/teléfono suelto
    U = [(t.upper(), b, pal) for t, b, pal in lineas]
    revisar = []
    # 1) Encabezado (diseño fijo del POS): NIT, dirección y teléfono van entre «PROPIETARIO DEL NEGOCIO» y «RECIBO #»;
    #    esa franja se tapa SIEMPRE, se hayan leído o no. Sin las dos líneas → «revisar».
    cab = next((b for t, b, _ in U if re.search(r"PROPIET|NEGOC", t)), None)
    rec = next((b for t, b, _ in U if re.search(r"\bREC[I1L]|ECIB|BO\s*#", t)), None)
    if rec is None:                         # «RECIBO #» ilegible: queda justo encima de «ORIGINAL»
        ori = next((b for t, b, _ in U if re.search(r"OR[I1L]G[I1L]N", t)), None)
        if ori: rec = (ori[0], int(ori[1] - 1.5 * (ori[3] - ori[1])) - 2, ori[2], ori[1])
    if cab and rec and cab[3] < rec[1]:
        dib.rectangle((0, cab[3] + 1, img.width, rec[1] - 2), fill="white"); tapadas.append("(franja NIT/dirección/teléfono)")
    else: revisar.append("sin encabezado")
    # 2) Domicilio: nombre, identificación, dirección y barrio del cliente → desde «Servicio a Domicilio» hasta «Valor:»
    serv = next((b for t, b, _ in U if "SERVIC" in t and "DOMIC" in t), None)
    if serv:
        fin = next((b[1] for t, b, _ in U if b[1] > serv[3] and re.search(r"VALOR|OBSERVAC", t)), img.height)
        if fin > serv[3] + 2: dib.rectangle((0, serv[3] + 1, img.width, fin - 2), fill="white"); tapadas.append("(datos del domicilio)")
    elif any(re.search(r"NOMBRE|BARRIO|MZ|LOTE|CLL|CALLE", t) for t, _, _ in U): revisar.append("domicilio sin «Servicio a Domicilio»")
    # 3) <NOMBRE> en los platos: «THE BIG <NOMBRE> BURGER» (entre BIG y BURGER) y «<NOMBRE> CRUNCHY» (antes de CRUNCHY)
    for t, (x0, y0, x1, y1), pal in U:
        ws = [(w.upper(), b) for w, b in pal]
        big = next((b for w, b in ws if re.fullmatch(r"\W*B[I1L]G\W*", w)), None)
        bur = next((b for w, b in ws if w.startswith("BURG") and big and b[0] > big[2]), None)
        if big and bur: dib.rectangle((big[2] + 1, y0 - 2, bur[0] - 1, y1 + 2), fill="white"); tapadas.append("(<NOMBRE> en BIG … BURGER)")
        elif big: revisar.append("BIG sin BURGER")
        cru = next((b for w, b in ws if w.startswith("CRUNCH")), None)
        if cru:
            ini = next((b[0] for w, b in ws if b[2] < cru[0] and w.strip("|[]!") ), cru[0])
            dib.rectangle((max(0, ini - 2), y0 - 2, cru[0] - 1, y1 + 2), fill="white"); tapadas.append("(<NOMBRE> antes de CRUNCHY)")
    # 4) Cliente con nombre (no «consumidor final») cuya identificación no se tapó → «revisar»
    sup = " ".join(tapadas).upper()
    cliente = next((t for t, _, _ in U if "CLIENTE" in t), None)
    if cliente and not re.search(r"CONS\w*\s*FINAL|CONSUMIDOR", cliente) and "IDENTIFICAC" not in sup: revisar.append("cliente con nombre")
    if revisar: return img, "revisar", tapadas + ["REVISAR: " + ", ".join(revisar)]
    return img, "ok", tapadas


def _slug(foto: str, pagina: int, i: int) -> str:
    return re.sub(r"[^\w-]+", "_", f"{foto}_p{pagina}")[:90] + f"_{i:02d}"


def _elegidas(peores: int):
    import medir_precision as mp
    libro = json.loads((DATOS / "libro.json").read_text(encoding="utf-8"))
    ref = json.loads((DATOS / "referencia" / "referencia_2026-09.json").read_text(encoding="utf-8"))
    return sorted(mp.mas_dudosas(libro, ref, peores))


def preparar(fotos: Path, peores: int):
    from PIL import Image
    from ocr_module import orientacion
    from parser_module.contable.validar import numeros_de_nombre
    (CARPETA / "recortes").mkdir(parents=True, exist_ok=True)
    man = {"fotos": {}}
    for foto, pagina in _elegidas(peores):
        ruta = fotos / foto
        png, _ = orientacion.preparar_pagina(ruta.read_bytes(), "auto")
        esp = numeros_de_nombre(ruta.name) if ruta.parent.name in ("comandas", "comanda") else None
        trozos = orientacion.separar(Image.open(io.BytesIO(png)).convert("RGB"), esperados=len(esp) if esp else None)
        filas = []
        for i, t in enumerate(trozos):
            limpio, estado, tapadas = tapar(t)
            nombre = _slug(foto, pagina, i) + ".png"; limpio.save(CARPETA / "recortes" / nombre)
            filas.append({"recorte": nombre, "estado": estado, "tapadas": tapadas})
        man["fotos"][f"{foto}|{pagina}"] = filas
        print(f"{foto}: {len(filas)} recortes, revisar {sum(f['estado'] != 'ok' for f in filas)}")
    MANIFIESTO.write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding="utf-8")
    _hoja_contacto(man)


def _hoja_contacto(man):
    """Una imagen por foto (recortes tapados lado a lado, el encabezado arriba) para revisar a ojo antes de enviar."""
    from PIL import Image, ImageDraw
    sal = CARPETA / "contacto"; sal.mkdir(exist_ok=True)
    for k, filas in man["fotos"].items():
        ims = [Image.open(CARPETA / "recortes" / f["recorte"]) for f in filas]
        ims = [im.crop((0, 0, im.width, min(im.height, 260))) for im in ims]           # solo el encabezado
        h = max(im.height for im in ims) + 20; hoja = Image.new("RGB", (sum(im.width + 8 for im in ims), h), "white")
        x = 0; d = ImageDraw.Draw(hoja)
        for im, f in zip(ims, filas):
            hoja.paste(im, (x, 20)); d.text((x + 2, 2), f["estado"], fill="green" if f["estado"] == "ok" else "red"); x += im.width + 8
        hoja.save(sal / (re.sub(r"[^\w-]+", "_", k)[:90] + ".png"))
    print(f"hojas de contacto: {sal}")


def enviar(maximo: int):
    import requests
    man = json.loads(MANIFIESTO.read_text(encoding="utf-8")); clave = _clave()
    (CARPETA / "respuestas").mkdir(exist_ok=True); n = 0
    for filas in man["fotos"].values():
        for f in filas:
            dest = CARPETA / "respuestas" / f["recorte"].replace(".png", ".json")
            if f["estado"] != "ok" or dest.exists(): continue
            if n >= maximo: print(f"tope de {maximo} llamadas"); return
            b64 = base64.b64encode((CARPETA / "recortes" / f["recorte"]).read_bytes()).decode()
            r = None
            for intento in range(5):            # la red se corta a ratos: 5 intentos con espera creciente
                try:                            # la clave va en cabecera, no en la URL (no sale en errores ni logs)
                    r = requests.post(URL, headers={"X-Goog-Api-Key": clave}, timeout=60,
                                      json={"requests": [{"image": {"content": b64}, "features": [{"type": "DOCUMENT_TEXT_DETECTION"}]}]})
                    break
                except requests.exceptions.RequestException as e:
                    print(f"  {f['recorte'][:40]}: {type(e).__name__}, intento {intento + 1}/5", flush=True)
                    import time; time.sleep(5 * (intento + 1))
            if r is None: sys.exit(f"sin conexión tras 5 intentos; {n} llamadas hechas (se puede volver a correr: no repite)")
            n += 1
            if not r.ok: sys.exit(f"HTTP {r.status_code}: {r.json().get('error', {}).get('message', '')[:300]}")
            res = r.json()["responses"][0]
            if "error" in res: sys.exit(f"{f['recorte']}: {res['error']}")
            dest.write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")
    print(f"{n} llamadas")


def por_filas(res: dict) -> str:
    """El texto de Google rearmado por filas (palabras con el centro a la misma altura), izquierda → derecha: en un recibo,
    la etiqueta y su monto quedan en la misma línea aunque Google los ponga en bloques distintos."""
    ps = []
    for p in res.get("fullTextAnnotation", {}).get("pages", []):
        for bl in p["blocks"]:
            for pa in bl["paragraphs"]:
                for w in pa["words"]:
                    v = w["boundingBox"].get("vertices", []); xs = [q.get("x", 0) for q in v]; ys = [q.get("y", 0) for q in v]
                    ps.append(((min(ys) + max(ys)) / 2, min(xs), max(ys) - min(ys), "".join(s["text"] for s in w["symbols"])))
    ps.sort(); filas = []
    for y, x, h, t in ps:
        if filas and abs(y - filas[-1][0]) <= max(4, 0.5 * h): filas[-1][1].append((x, t))
        else: filas.append([y, [(x, t)]])
    return "\n".join(" ".join(t for _, t in sorted(f[1])) for f in filas)


def medir(fotos: Path, peores: int):
    import medir_precision as mp
    from parser_module.contable import MARCA
    man = json.loads(MANIFIESTO.read_text(encoding="utf-8"))
    for nombre, texto_de in (("google", lambda r: r.get("fullTextAnnotation", {}).get("text", "")), ("google_filas", por_filas)):
        def leer(ruta, pagina, motor, texto_de=texto_de):
            foto = ruta.relative_to(fotos).as_posix(); out = []
            for f in man["fotos"].get(f"{foto}|{pagina}", []):
                j = CARPETA / "respuestas" / f["recorte"].replace(".png", ".json")
                if j.exists(): out.append(texto_de(json.loads(j.read_text(encoding="utf-8"))))
            return f"\n{MARCA}\n".join(out)
        inf = mp.ejecutar("2026-09", fotos, None, leer, variante=nombre, peores=peores)
        print(f"{nombre}: omitidos {inf['omitidos']} · dudosos {inf['dudosos']} · validados con error {inf['validados_con_error']} → {inf['archivo']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("paso", choices=("preparar", "enviar", "medir"))
    ap.add_argument("--fotos", default="D:/Claude/image_to_text/data/SEPTIEMBRE"); ap.add_argument("--peores", type=int, default=20)
    ap.add_argument("--max", type=int, default=150)
    a = ap.parse_args()
    {"preparar": lambda: preparar(Path(a.fotos), a.peores), "enviar": lambda: enviar(a.max),
     "medir": lambda: medir(Path(a.fotos), a.peores)}[a.paso]()
