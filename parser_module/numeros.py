"""Utilidades de bajo nivel: normalizar texto, leer cifras ($1.250.000, 120k, 'cien mil'), fechas."""
from __future__ import annotations
import re, unicodedata, datetime
from dataclasses import dataclass, field


def norm(s: str) -> str:
    """minúsculas y sin tildes, SIN cambiar la longitud (las posiciones siguen valiendo)."""
    out = []
    for ch in s:
        if ch in "°ºª":
            out.append(" "); continue
        base = "".join(c for c in unicodedata.normalize("NFD", ch) if unicodedata.category(c) != "Mn").lower()
        out.append(base if len(base) == 1 else (ch.lower() if len(ch.lower()) == 1 else " "))
    return "".join(out)


# ── números escritos con palabras ────────────────────────────────────────────
_UNI = {"cero": 0, "un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7,
        "ocho": 8, "nueve": 9, "diez": 10, "once": 11, "doce": 12, "trece": 13, "catorce": 14, "quince": 15,
        "dieciseis": 16, "diecisiete": 17, "dieciocho": 18, "diecinueve": 19, "veinte": 20, "veintiun": 21,
        "veintiuno": 21, "veintiuna": 21, "veintidos": 22, "veintitres": 23, "veinticuatro": 24, "veinticinco": 25,
        "veintiseis": 26, "veintisiete": 27, "veintiocho": 28, "veintinueve": 29}
_TENS = {"treinta": 30, "cuarenta": 40, "cincuenta": 50, "sesenta": 60, "setenta": 70, "ochenta": 80, "noventa": 90}
_HUND = {"cien": 100, "ciento": 100, "doscientos": 200, "doscientas": 200, "trescientos": 300, "trescientas": 300,
         "cuatrocientos": 400, "cuatrocientas": 400, "quinientos": 500, "quinientas": 500, "seiscientos": 600,
         "seiscientas": 600, "setecientos": 700, "setecientas": 700, "ochocientos": 800, "ochocientas": 800,
         "novecientos": 900, "novecientas": 900}
_NW = "|".join(sorted(list(_UNI) + list(_TENS) + list(_HUND) + ["mil", "millones", "millon"], key=len, reverse=True))
_RUN = re.compile(rf"(?<![a-z])(?:{_NW})(?:\s+(?:y\s+)?(?:{_NW}))*(?![a-z])")


def _valor_palabras(words):
    total = cur = 0
    for w in words:
        if w in _UNI: cur += _UNI[w]
        elif w in _TENS: cur += _TENS[w]
        elif w in _HUND: cur += _HUND[w]
        elif w == "mil": total += (cur or 1) * 1000; cur = 0
        elif w in ("millon", "millones"): total += (cur or 1) * 1_000_000; cur = 0
    return total + cur


def words_to_digits(s: str) -> str:
    def rep(m):
        run = m.group(0)
        words = [w for w in run.split() if w != "y"]
        if len(words) == 1 and words[0] in ("un", "una", "uno"):
            return run
        if words[0] in ("mil", "millon", "millones") and re.search(r"\d\s*$", s[:m.start()]):
            return run                      # "120 mil": lo resuelve el sufijo
        return f" {_valor_palabras(words)} "
    return _RUN.sub(rep, s)


_OCR = re.compile(r"(?<![a-z])(?=[\d.,'ol]*\d)[\d.,'ol]{2,}(?![a-z])")


def fix_ocr_digits(s: str) -> str:
    """'85O.OOO' → '850.000', '6l' → '61' (solo dentro de cifras)."""
    return _OCR.sub(lambda m: m.group(0).replace("o", "0").replace("l", "1"), s)


# ── montos ───────────────────────────────────────────────────────────────────
_AMT = re.compile(
    r"(?<![\w/])(-)?(?:\$\s*)?(\d{1,3}(?:[.,'´’ ]\d{3})+(?:[.,]\d{1,2})?(?!\d)|\d+(?:[.,]\d+)?)"
    r"(?:\s*(k|mil|millones|millon|mm)(?![a-z]))?(?![\w/%])")


@dataclass
class Monto:
    start: int
    end: int
    valor: int
    texto: str
    flags: list = field(default_factory=list)
    neg: bool = False          # «-$138,950»: el signo va pegado al número


def parse_monto(tok: str, suf: str | None):
    flags = []
    t = tok.strip()
    m = re.fullmatch(r"(\d{1,3}(?:[.,'´’ ]\d{3})+)(?:[.,](\d{1,2}))?", t)
    if m:
        n = float(re.sub(r"[.,'´’ ]", "", m.group(1)))
        if m.group(2): n += float("0." + m.group(2)); flags.append("decimal")
    elif re.fullmatch(r"\d+[.,]\d+", t):
        n = float(t.replace(",", ".")); flags.append("decimal")
    else:
        n = float(re.sub(r"\D", "", t) or 0)
    suf = (suf or "").lower()
    if suf in ("k", "mil"): n *= 1000
    elif suf in ("millon", "millones", "mm"): n *= 1_000_000
    return int(round(n)), flags


def find_amounts(p: str) -> list[Monto]:
    groups: list[Monto] = []
    for m in _AMT.finditer(p):
        v, fl = parse_monto(m.group(2), m.group(3))
        if groups:
            g = groups[-1]; gap = p[g.end:m.start()]
            if re.fullmatch(r"\s*\+\s*", gap):
                g.valor += v; g.end = m.end(); g.texto = p[g.start:g.end].strip(); g.flags += ["suma"] + fl
                continue
            if re.fullmatch(r"\s*=\s*", gap):
                if g.valor != v: g.flags.append("suma no coincide")
                g.valor = v; g.end = m.end(); g.texto = p[g.start:g.end].strip(); continue
        groups.append(Monto(m.start(), m.end(), v, m.group(0).strip(), fl, bool(m.group(1))))
    return groups


# ── fechas ───────────────────────────────────────────────────────────────────
_MES = {"enero": 1, "ene": 1, "febrero": 2, "feb": 2, "marzo": 3, "mar": 3, "abril": 4, "abr": 4, "mayo": 5, "may": 5,
        "junio": 6, "jun": 6, "julio": 7, "jul": 7, "agosto": 8, "ago": 8, "septiembre": 9, "setiembre": 9,
        "sept": 9, "sep": 9, "octubre": 10, "oct": 10, "noviembre": 11, "nov": 11, "diciembre": 12, "dic": 12}
_MN = "|".join(sorted(_MES, key=len, reverse=True))
_D = [
    (re.compile(r"(?<![\d.,/])(\d{1,2})\s*[/\-]\s*(\d{1,2})\s*[/\-]\s*(\d{4}|\d{2})(?![\d/])"), "dmy"),
    (re.compile(r"(?<![\d.,/])(\d{1,2})\.(\d{1,2})\.(\d{4})(?!\d)"), "dmy"),
    (re.compile(rf"(?<![a-z\d])(\d{{1,2}})[\s\-./]*(?:de\s+)?({_MN})\.?(?:[\s\-./,]*(?:de|del)?\s*(\d{{4}}|\d{{2}}))?(?![a-z\d])"), "dMy"),
    (re.compile(rf"(?<![a-z])({_MN})\.?\s*(\d{{1,2}})(?:\s*,?\s*(\d{{4}}))?(?![\d])"), "Mdy"),
    (re.compile(r"(?<![\d.,/])(\d{1,2})\s*/\s*(\d{1,2})(?![\d/.])"), "dm"),
]


def extraer_fecha(s: str, anio: int | None = None):
    """Devuelve (iso|None, s con la fecha tapada con espacios). Día primero (formato colombiano)."""
    anio = anio or datetime.date.today().year
    for rx, kind in _D:
        for m in rx.finditer(s):
            g = m.groups()
            try:
                if kind == "dmy": d, mo, y = int(g[0]), int(g[1]), g[2]
                elif kind == "dMy": d, mo, y = int(g[0]), _MES[g[1]], g[2]
                elif kind == "Mdy": mo, d, y = _MES[g[0]], int(g[1]), g[2]
                else: d, mo, y = int(g[0]), int(g[1]), None
                y = (2000 + int(y) if y and len(y) == 2 else int(y)) if y else anio
                iso = datetime.date(y, mo, d).isoformat()
            except (ValueError, KeyError):
                continue
            return iso, s[:m.start()] + " " * (m.end() - m.start()) + s[m.end():]
    return None, s


_HORA = re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?(?:\s*[ap]\.?\s?m\.?)?")


def tapar_horas(s: str) -> str:
    return _HORA.sub(lambda m: " " * len(m.group(0)), s)
