"""Páginas escaneadas: gira lo que está de lado o al revés, recorta los márgenes blancos y separa los papeles de una hoja.
El giro automático usa Tesseract (detección de orientación) si está instalado; si no, se puede girar a mano."""
from __future__ import annotations
import io, re, shutil
import numpy as np
from PIL import Image

CONFIANZA_MIN = 0.8      # con tus escaneos: aciertos ≥ 1.0 y el único caso dudoso (hoja con papeles mezclados) dio 0.03


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


def preparar_pagina(data: bytes, giro="auto") -> tuple:
    """bytes de una imagen → (bytes PNG listos para el OCR, grados aplicados). giro: 'auto' o 0/90/180/270 (horario).
    La orientación se detecta en la hoja COMPLETA (recortada se equivocaba en hojas con papeles mezclados) y luego se recortan los márgenes."""
    img = Image.open(io.BytesIO(data)).convert("RGB")
    if giro == "auto":
        g, conf = giro_automatico(img); g = g if conf >= CONFIANZA_MIN else 0
    else:
        g = int(giro) % 360
    if g: img = img.rotate(-g, expand=True)          # PIL gira en sentido antihorario: -g = horario
    img = recortar(img)
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


def _por_columnas(tinta, esperados):
    """T8b · Papeles en columnas que se tocan o se escalonan (las fotos de comandas): columnas por valles de tinta; dentro de
    cada columna, los `esperados − columnas` huecos más anchos de toda la hoja, sin dejar un papel de menos de 15 % del alto."""
    H, W = tinta.shape
    px = _suave(tinta.sum(0), 5); med = np.median(px[px > 0])
    cols, ini = [], 0
    for a, b in _huecos(px, max(4, int(0.015 * W)), 0.25 * med): cols.append((ini, a)); ini = b
    cols.append((ini, W)); cols = [c for c in cols if c[1] - c[0] >= 0.08 * W]
    if not cols or esperados < len(cols): return []
    cand, perfiles = [], []
    for ci, (a, b) in enumerate(cols):
        raw = tinta[:, a:b].sum(1); py = _suave(raw, 3); perfiles.append(raw)
        m = np.median(py[py > 0]) if (py > 0).any() else 0
        cand += [(g1 - g0, ci, (g0 + g1) // 2) for g0, g1 in _huecos(py, max(3, int(0.01 * H)), 0.2 * m)]
    cortes, falta = {ci: [] for ci in range(len(cols))}, esperados - len(cols)
    for _, ci, y in sorted(cand, reverse=True):
        if falta <= 0: break
        if _alto_tinta(perfiles[ci], cortes[ci] + [y], H) >= 0.15 * H: cortes[ci].append(y); falta -= 1
    cajas = []
    for ci, (a, b) in enumerate(cols):
        bordes = [0] + sorted(cortes[ci]) + [H]
        for y0, y1 in zip(bordes, bordes[1:]):
            sub = tinta[y0:y1, a:b]
            if not sub.any(): continue
            ys = np.nonzero(sub.sum(1))[0]; xs = np.nonzero(sub.sum(0))[0]
            cajas.append((a + int(xs[0]), y0 + int(ys[0]), a + int(xs[-1]) + 1, y0 + int(ys[-1]) + 1))
    return cajas


def separar(img: Image.Image, max_papeles: int = 8, esperados: int | None = None) -> list:
    """Parte una hoja con VARIOS papeles (recibos lado a lado) en un recorte por papel, en orden de lectura.
    Si no encuentra separaciones claras devuelve la hoja entera.
    `esperados`: cuántos papeles trae la foto según su nombre («85297 al 85302» → 6). Con él se parte por columnas y los
    huecos más anchos (T8b: de 2 % a 81 % de fotos de septiembre con la cuenta exacta); sin él, o si no sale, lo de siempre."""
    f = 3
    g = np.asarray(img.convert("L").resize((max(1, img.width // f), max(1, img.height // f))), dtype=float)
    tinta = g < 165
    total = tinta.sum()
    if total < 200: return [img]
    if esperados and 2 <= esperados <= max_papeles:
        H, W = tinta.shape
        limpia = tinta & ~_lineas(tinta, max(10, int(0.06 * H)), 0) & ~_lineas(tinta, max(10, int(0.06 * W)), 1)
        tl = limpia.sum()
        cajas = [c for c in _por_columnas(limpia, esperados) if limpia[c[1]:c[3], c[0]:c[2]].sum() >= max(150, 0.03 * tl)]
        if 2 <= len(cajas) <= max_papeles and all(min(c[2] - c[0], c[3] - c[1]) * f >= 150 for c in cajas):
            return _recortes(img, cajas, tinta.shape[0], f)
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


def _recortes(img, cajas, alto, f) -> list:
    cajas = sorted(cajas, key=lambda c: (round(c[1] / (alto * 0.25)), c[0]))   # filas de arriba abajo, y de izquierda a derecha
    out = []
    for x0, y0, x1, y1 in cajas:
        r = img.crop((max(0, (x0 - 6) * f), max(0, (y0 - 6) * f), min(img.width, (x1 + 6) * f), min(img.height, (y1 + 6) * f)))
        out.append(recortar(r))
    return out
