"""Páginas escaneadas: gira lo que está de lado o al revés, recorta los márgenes blancos y separa los papeles de una hoja.
El giro automático usa Tesseract (detección de orientación) si está instalado; si no, se puede girar a mano."""
from __future__ import annotations
import io, re, shutil
import numpy as np
from PIL import Image

CONFIANZA_MIN = 0.8      # con tus escaneos: aciertos ≥ 1.0 y el único caso dudoso (hoja con papeles mezclados) dio 0.03
INCL_MIN = 0.3           # ADR-018: con giro 0 y menos de esto la hoja no se toca (mismos recortes que v1.6.0)


def tesseract_disponible() -> bool:
    try:
        import pytesseract  # noqa: F401
    except ImportError:
        return False
    return shutil.which("tesseract") is not None


def giro_automatico(img: Image.Image) -> tuple:
    """(grados en sentido horario para dejar el texto derecho, confianza). (0, 0.0) si no se puede saber."""
    if not tesseract_disponible():
        return 0, 0.0
    import pytesseract
    chico = img.copy(); chico.thumbnail((2600, 2600))      # a resolución completa: en miniaturas se equivocaba
    try:
        osd = pytesseract.image_to_osd(chico.convert("RGB"), config="--psm 0 -c min_characters_to_try=20")
        return int(re.search(r"Rotate: (\d+)", osd).group(1)), float(re.search(r"Orientation confidence: ([\d.]+)", osd).group(1))
    except Exception:  # noqa: BLE001  (poco texto, idioma osd ausente…)
        return 0, 0.0


def _tesseract(img) -> tuple:
    """`detectar` por defecto: (giro, confianza, inclinación 0.0) con el OSD de Tesseract, como en v1.6.0."""
    return (*giro_automatico(img), 0.0)


def enderezar(img: Image.Image, g: int, incl: float) -> Image.Image:
    """Gira `g` grados en sentido horario y luego `incl` grados con el signo de PIL.rotate, sobre fondo blanco (ADR-018, T5)."""
    if g: img = img.rotate(-g, expand=True)          # PIL gira en sentido antihorario: -g = horario
    if abs(incl) >= INCL_MIN: img = img.rotate(incl, expand=True, fillcolor="white", resample=Image.BICUBIC)
    return img


def recortar(img: Image.Image, margen: float = 0.02) -> Image.Image:
    """Quita el blanco alrededor del contenido (ignora motas y bordes del escáner usando cuantiles de la tinta)."""
    g = np.asarray(img.convert("L").resize((max(1, img.width // 3), max(1, img.height // 3))), dtype=float)
    tinta = g < 165
    if tinta.sum() < 50:
        return img
    def span(p):
        c = np.cumsum(p); t = c[-1]
        return int(np.searchsorted(c, t * 0.004)), int(np.searchsorted(c, t * 0.996))
    y0, y1 = span(tinta.sum(1).astype(float)); x0, x1 = span(tinta.sum(0).astype(float))
    my, mx = int((y1 - y0 + 1) * margen) + 4, int((x1 - x0 + 1) * margen) + 4
    box = (max(0, (x0 - mx) * 3), max(0, (y0 - my) * 3), min(img.width, (x1 + mx + 1) * 3), min(img.height, (y1 + my + 1) * 3))
    return img.crop(box) if (box[2] - box[0]) > 80 and (box[3] - box[1]) > 80 else img


def preparar_pagina(data: bytes, giro="auto", detectar=None) -> tuple:
    """bytes de una imagen → (bytes PNG listos para el OCR, grados aplicados). giro: 'auto' o 0/90/180/270 (horario).
    La orientación se detecta en la hoja COMPLETA (recortada se equivocaba en hojas con papeles mezclados) y luego se recortan los márgenes.
    `detectar(img) -> (giro, confianza, inclinación)` (M-25: motores.detectar_giro); sin él, Tesseract sin inclinación."""
    img = Image.open(io.BytesIO(data)).convert("RGB")
    incl = 0.0
    if giro == "auto":
        g, conf, incl = (detectar or _tesseract)(img)
        if conf < CONFIANZA_MIN: g, incl = 0, 0.0
    else:
        g = int(giro) % 360
    img = recortar(enderezar(img, g, incl))
    b = io.BytesIO(); img.save(b, "PNG"); return b.getvalue(), g


def _huecos(prof, largo_min, tol):
    """Rangos vacíos (≥ largo_min) que NO tocan los bordes: son separaciones entre papeles."""
    out, i, n = [], 0, len(prof)
    while i < n:
        if prof[i] <= tol:
            j = i
            while j < n and prof[j] <= tol: j += 1
            if j - i >= largo_min and i > 0 and j < n: out.append((i, j))
            i = j
        else: i += 1
    return out


def _xy(tinta, x0, y0, x1, y1, nivel=0):
    if nivel > 4: return [(x0, y0, x1, y1)]
    sub = tinta[y0:y1, x0:x1]
    for eje in (1, 0):                                   # 1: papeles lado a lado (columnas) · 0: papeles apilados (filas)
        prof = sub.sum(axis=0 if eje == 1 else 1); n = prof.size
        ancho = sub.shape[0] if eje == 1 else sub.shape[1]
        hu = _huecos(prof, max(6, int((0.02 if eje == 1 else 0.045) * n)), max(2, int(0.004 * ancho)))
        if hu:
            partes, ini = [], 0
            for a, b in hu: partes.append((ini, a)); ini = b
            partes.append((ini, n)); res = []
            for a, b in partes:
                if b - a >= 8: res += _xy(tinta, x0 + a, y0, x0 + b, y1, nivel + 1) if eje == 1 else _xy(tinta, x0, y0 + a, x1, y0 + b, nivel + 1)
            return res
    return [(x0, y0, x1, y1)]


def _ventana(t, L, eje):
    """Suma de L celdas seguidas a lo largo de `eje` (sumas acumuladas; sale n − L + 1 a lo largo del eje)."""
    c = np.cumsum(t, axis=eje, dtype=np.int32); n = t.shape[eje]
    c = np.concatenate([np.zeros_like(c.take([0], axis=eje)), c], axis=eje)
    return c.take(range(L, n + 1), axis=eje) - c.take(range(0, n - L + 1), axis=eje)


def _lineas(t, L, eje):
    """Píxeles de un trazo recto de ≥ L a lo largo de `eje`: bordes y sombras de los papeles, que tapan los huecos entre ellos."""
    if t.shape[eje] <= L: return np.zeros_like(t)
    lleno = (_ventana(t, L, eje) == L).astype(np.int32)
    pad = [(0, 0), (0, 0)]; pad[eje] = (L - 1, L - 1)
    return _ventana(np.pad(lleno, pad), L, eje) > 0


def _suave(p, k): return np.convolve(p.astype(float), np.ones(k) / k, "same")


def _alto_tinta(prof, cortes, n) -> int:
    """El tramo con tinta más bajo que dejan estos cortes."""
    b = [0] + sorted(cortes) + [n]; altos = []
    for a, z in zip(b, b[1:]):
        ys = np.nonzero(prof[a:z])[0]; altos.append(0 if ys.size == 0 else ys[-1] - ys[0] + 1)
    return min(altos)


def _caja(g, k):
    """Media en una ventana k×k (mismo tamaño que g; sumas acumuladas)."""
    p = k // 2; c = np.pad(g.astype(float), p, mode="edge").cumsum(0).cumsum(1); c = np.pad(c, ((1, 0), (1, 0)))
    H, W = g.shape
    return (c[k:k + H, k:k + W] - c[:H, k:k + W] - c[k:k + H, :W] + c[:H, :W]) / (k * k)


def _otsu(v) -> int:
    h, _ = np.histogram(v, 256, (0, 256)); p = h / max(1, h.sum()); w = np.cumsum(p); m = np.cumsum(p * np.arange(256))
    return int(np.argmax((m[-1] * w - m) ** 2 / np.maximum(w * (1 - w), 1e-9)))


def _tinta_en_papel(rgb):
    """M-11 · Tinta solo DENTRO de los papeles: la madera (color: ≥ 30 % de píxeles saturados alrededor) no es papel, y en
    las fotos sin escanear (mesa oscura, papel gris) el papel es lo claro según Otsu del brillo local y la tinta lo que
    queda ≥ 25 niveles por debajo de su papel. Con g < 165 a secas la textura de la mesa contaba como tinta."""
    a = rgb.astype(float); g = a @ np.array([0.299, 0.587, 0.114])
    mx = a.max(2); sat = (mx - a.min(2)) / np.maximum(mx, 1)
    H, W = g.shape; k = max(9, int(0.05 * min(H, W)) | 1)
    papel = _caja(sat > 0.15, k) < 0.3
    if np.median(g) < 200:                               # foto cruda: mesa oscura alrededor del papel
        fondo = _caja(g, k); papel &= fondo > _otsu(fondo)
        return papel & (g < np.minimum(165, _caja(g, 15) - 25))
    return papel & (g < 165)


def _equilibrio(cajas) -> float:
    """Área del papel más chico / la del más grande (1 = todos iguales)."""
    ar = [(c[2] - c[0]) * (c[3] - c[1]) for c in cajas]
    return min(ar) / max(ar) if ar and max(ar) else 0.0


def _masa_min(prof, cortes, n) -> float:
    """La tinta del tramo más pobre que dejan estos cortes."""
    b = [0] + sorted(cortes) + [n]
    return min(float(prof[a:z].sum()) for a, z in zip(b, b[1:]))


def _por_columnas(tinta, esperados, masa=0.0, cantos=None):
    """T8b · Papeles en columnas que se tocan o se escalonan (las fotos de comandas): columnas por valles de tinta; dentro de
    cada columna, los `esperados − columnas` huecos más anchos de toda la hoja, sin dejar un papel de menos de 15 % del alto."""
    H, W = tinta.shape
    px = _suave(tinta.sum(0), 5); med = np.median(px[px > 0])
    cols, ini = [], 0
    for a, b in _huecos(px, max(4, int(0.015 * W)), 0.25 * med): cols.append((ini, a)); ini = b
    cols.append((ini, W)); cols = [c for c in cols if c[1] - c[0] >= 0.08 * W]
    if not cols or len(cols) > esperados + 1: return []   # una columna de más: un papel que no está en el nombre (Rappi)
    cand, perfiles = [], []
    for ci, (a, b) in enumerate(cols):
        raw = tinta[:, a:b].sum(1); py = _suave(raw, 3); perfiles.append(raw)
        m = np.median(py[py > 0]) if (py > 0).any() else 0
        canto = lambda g0, g1: cantos is not None and cantos[max(0, g0 - 12):g1 + 12, a:b].any(0).mean() >= 0.8   # M-11: canto de papel (algo torcido) de lado a lado
        cand += [(g1 - g0 + (0.06 * H if canto(g0, g1) else 0), ci, (g0 + g1) // 2) for g0, g1 in _huecos(py, max(3, int(0.01 * H)), 0.2 * m)]
    cortes, falta = {ci: [] for ci in range(len(cols))}, esperados - len(cols)
    for _, ci, y in sorted(cand, reverse=True):
        if falta <= 0: break
        if _alto_tinta(perfiles[ci], cortes[ci] + [y], H) >= 0.15 * H and _masa_min(perfiles[ci], cortes[ci] + [y], H) >= masa * tinta.sum() / esperados:
            cortes[ci].append(y); falta -= 1                # masa (M-11): un tramo con cuatro motas de mesa no es un papel
    cajas = []
    for ci, (a, b) in enumerate(cols):
        bordes = [0] + sorted(cortes[ci]) + [H]
        for y0, y1 in zip(bordes, bordes[1:]):
            sub = tinta[y0:y1, a:b]
            if not sub.any(): continue
            ys = np.nonzero(sub.sum(1))[0]; xs = np.nonzero(sub.sum(0))[0]
            cajas.append((a + int(xs[0]), y0 + int(ys[0]), a + int(xs[-1]) + 1, y0 + int(ys[-1]) + 1))
    return cajas


def separar(img: Image.Image, max_papeles: int = 8, esperados: int | None = None, detectar=None) -> list:
    """Parte una hoja con VARIOS papeles (recibos lado a lado) en un recorte por papel, en orden de lectura.
    Si no encuentra separaciones claras devuelve la hoja entera.
    `esperados`: cuántos papeles trae la foto según su nombre («85297 al 85302» → 6). Con él se parte por columnas y los
    huecos más anchos (T8b: de 2 % a 81 % de fotos de septiembre con la cuenta exacta); sin él, o si no sale, lo de siempre.
    `detectar`: como en preparar_pagina; vota el giro de los papeles de lado."""
    f = 3
    g = np.asarray(img.convert("L").resize((max(1, img.width // f), max(1, img.height // f))), dtype=float)
    tinta = g < 165
    total = tinta.sum()
    if total < 200: return [img]
    if esperados and 2 <= esperados <= max_papeles:
        rgb = np.asarray(img.convert("RGB").resize((tinta.shape[1], tinta.shape[0])))
        papel = _tinta_en_papel(rgb)
        opciones = []
        for nombre, t in (("papel", papel), ("tinta", tinta), ("de lado", papel.T)):   # M-11: tinta en papel; la de T8b; la foto de lado
            H, W = t.shape
            horiz = _lineas(t, max(10, int(0.06 * W)), 1)
            limpia = t & ~_lineas(t, max(10, int(0.06 * H)), 0) & ~horiz
            tl = limpia.sum()
            if tl < 200: continue
            m9 = nombre != "tinta"                       # la ruta de T8b queda igual
            cajas = [c for c in _por_columnas(limpia, esperados, 0.3 if m9 else 0.0, horiz if m9 else None) if limpia[c[1]:c[3], c[0]:c[2]].sum() >= max(150, 0.03 * tl)]
            if not (2 <= len(cajas) <= max_papeles and all(min(c[2] - c[0], c[3] - c[1]) * f >= 150 for c in cajas)): continue
            de_pie = np.mean([(c[3] - c[1]) > 1.2 * (c[2] - c[0]) for c in cajas])     # los recibos son más altos que anchos
            if nombre == "de lado": cajas = [(y0, x0, y1, x1) for x0, y0, x1, y1 in cajas]
            opciones.append((len(cajas) in (esperados, esperados + 1), de_pie, _equilibrio(cajas), cajas, nombre == "de lado"))
        buenas = [o for o in opciones if o[0] and o[1] >= 0.5 and o[2] >= 0.25]   # la cuenta (o una de más: Rappi), de pie, parejos
        if opciones:
            o = buenas[0] if buenas else max(opciones, key=lambda o: (o[0], o[2]))
            return _recortes(img, o[3], tinta.shape[0], f, de_lado=o[4], detectar=detectar)
    cajas = [c for c in _xy(tinta, 0, 0, tinta.shape[1], tinta.shape[0]) if tinta[c[1]:c[3], c[0]:c[2]].sum() >= max(150, 0.03 * total)]
    if len(cajas) >= 2:                                    # una caja mucho más ancha que las demás = recibos pegados: se corta en los «valles» de tinta
        ref = min(c[2] - c[0] for c in cajas); nuevas = []
        for c in cajas:
            ancho = c[2] - c[0]
            if ancho > 1.7 * ref and (c[3] - c[1]) <= 1.3 * ancho:       # solo bloques «anchos» (recibos pegados); las pilas de vales no se tocan
                n = max(2, round(ancho / ref)); prof = np.convolve(tinta[c[1]:c[3], c[0]:c[2]].sum(axis=0).astype(float), np.ones(5) / 5, "same"); cortes = []
                for k in range(1, n):
                    centro = int(k * ancho / n); ven = int(0.3 * ancho / n)
                    cortes.append(max(1, centro - ven) + int(np.argmin(prof[max(1, centro - ven):min(ancho - 1, centro + ven)])))
                bordes = [0] + sorted(cortes) + [ancho]
                nuevas += [(c[0] + bordes[i], c[1], c[0] + bordes[i + 1], c[3]) for i in range(len(bordes) - 1)]
            else: nuevas.append(c)
        cajas = nuevas
    if len(cajas) < 2 or len(cajas) > max_papeles or any(min(c[2] - c[0], c[3] - c[1]) * f < 150 for c in cajas): return [img]   # fragmentos pequeños = no es una separación fiable
    return _recortes(img, cajas, tinta.shape[0], f)


def _recortes(img, cajas, alto, f, de_lado=False, detectar=None) -> list:
    cajas = sorted(cajas, key=lambda c: (round(c[1] / (alto * 0.25)), c[0]))   # filas de arriba abajo, y de izquierda a derecha
    out = []
    for x0, y0, x1, y1 in cajas:
        r = img.crop((max(0, (x0 - 6) * f), max(0, (y0 - 6) * f), min(img.width, (x1 + 6) * f), min(img.height, (y1 + 6) * f)))
        out.append(recortar(r))
    if de_lado:                                          # M-11: papeles de lado que la hoja entera no giró: el giro que más papeles piden
        votos = [(g, i) for g, c, i in map(detectar or _tesseract, out) if c >= CONFIANZA_MIN and g in (90, 270)]
        if votos:
            giros = [v for v, _ in votos]; g = max(set(giros), key=giros.count)
            incls = sorted(i for v, i in votos if v == g); incl = incls[len(incls) // 2]   # la mediana de los que ganaron
            out = [enderezar(r, g, incl) for r in out]
            if abs(incl) >= INCL_MIN: out = [recortar(r) for r in out]                       # quita las esquinas blancas del giro
    return out
