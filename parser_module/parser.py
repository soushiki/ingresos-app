"""Módulo 2 · texto plano (del módulo 1) → los 12 campos del cierre de caja.

Estrategia: reglas robustas (sinónimos + tolerancia a errores de OCR + varias disposiciones de la planilla).
Todo lo dudoso se marca como «revisar»; nada se inventa.
"""
from __future__ import annotations
import difflib, re, statistics
from dataclasses import dataclass, field, asdict
from .campos import MODIFICADORES
from .lexico import SIGNO
from .config import Config
from .numeros import (Monto, extraer_fecha, find_amounts, fix_ocr_digits, norm, tapar_horas, words_to_digits)

ASSOC = {"der": 1.0, "izq": 0.9, "sig": 0.85, "ant": 0.8, "bloque": 0.8, "cero": 1.0}
PENAL = {"dudoso": 0.6, "tachado": 0.9, "decimal": 0.85, "cero por guion": 0.7, "varios numeros": 0.7,
         "bloque desalineado": 0.6, "miles": 0.6, "conteo alto": 0.6, "suma de partes": 0.9,
         "suma no coincide": 0.6, "valores distintos": 0.7, "signo no indicado (¿faltante o sobrante?)": 0.7}
UMBRAL_OK = 0.75
_CERO = re.compile(r"[\s:=._\-–—]*(?:-+|—|–|nada|ninguno|ninguna|no|n/?a|sin)[\s.]*")


@dataclass
class Campo:
    clave: str
    nombre: str
    valor: int | None = None
    crudo: str = ""
    linea: str = ""
    confianza: float = 0.0
    estado: str = "faltante"            # ok · revisar · faltante
    razones: list = field(default_factory=list)
    alternativas: list = field(default_factory=list)
    fuente: str = "reglas"


@dataclass
class Cierre:
    fecha: str | None
    campos: dict
    notas: list = field(default_factory=list)
    desconocidas: list = field(default_factory=list)   # [{"etiqueta","valor","linea"}] → enseñar con Config.aprender
    advertencias: list = field(default_factory=list)
    texto: str = ""
    fuente: str = ""
    orden: list = field(default_factory=list)      # claves de las columnas, en el orden del esquema
    nombres: dict = field(default_factory=dict)    # clave → nombre de la columna
    tipos: dict = field(default_factory=dict)      # clave → monto | conteo

    def valor(self, clave, cero=True):
        v = self.campos[clave].valor
        return 0 if (v is None and cero) else v

    def a_fila(self) -> dict:
        """Nombres de columna de Excel → valor (0 si falta)."""
        return {self.nombres[k]: self.valor(k) for k in self.orden}

    def por_revisar(self):
        return [k for k in self.orden if self.campos[k].estado != "ok"]

    def to_dict(self):
        return asdict(self)


@dataclass
class _Et:
    start: int; end: int; campo: str; alias: str; peso: float; ratio: float


@dataclass
class _Li:
    orig: str; p: str
    labels: list = field(default_factory=list)
    amts: list = field(default_factory=list)
    dudas: bool = False; ilegible: bool = False; tachado: bool = False
    kind: str = ""
    pend: list = field(default_factory=list)
    i: int = 0


class _Vocab:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.exact = []       # (campo, alias, peso, regex)
        self.fuzzy1, self.fuzzyn = [], []
        for campo, als in cfg.aliases.items():
            for alias, peso in als.items():
                toks = alias.split()
                rx = re.compile(r"(?<![a-z0-9])" + r"[\s.\-_]*".join(re.escape(t) for t in toks) + r"(?![a-z0-9])")
                self.exact.append((campo, alias, peso, rx))
                if len(toks) == 1 and len(alias) >= 5: self.fuzzy1.append((campo, alias, peso))
                elif len(toks) > 1 and len(alias) >= 7: self.fuzzyn.append((campo, alias, peso, len(toks)))
        self.parte = {(c, a) for c, s in cfg.partes.items() for a in s}


def _etiquetas(p: str, V: _Vocab) -> list[_Et]:
    cand = []
    for campo, alias, peso, rx in V.exact:
        for m in rx.finditer(p):
            cand.append(_Et(m.start(), m.end(), campo, alias, peso, 1.0))
    toks = [(m.start(), m.end(), m.group(0)) for m in re.finditer(r"[a-z]{4,}", p)]
    for i, (s, e, w) in enumerate(toks):                       # palabras sueltas mal leídas
        for campo, alias, peso in V.fuzzy1:
            if w[0] == alias[0] and abs(len(w) - len(alias)) <= 2 and w != alias:
                r = difflib.SequenceMatcher(None, w, alias).ratio()
                if r >= 0.84: cand.append(_Et(s, e, campo, alias, peso, r))
    for i in range(len(toks)):                                 # etiquetas de 2-3 palabras mal leídas
        for n in (2, 3):
            if i + n > len(toks): continue
            s, e = toks[i][0], toks[i + n - 1][1]
            if p[s:e].count("\n") or e - s > 40: continue
            w = " ".join(t[2] for t in toks[i:i + n])
            for campo, alias, peso, k in V.fuzzyn:
                if k == n and w[0] == alias[0] and w != alias:
                    r = difflib.SequenceMatcher(None, w, alias).ratio()
                    if r >= 0.86: cand.append(_Et(s, e, campo, alias, peso, r))
    cand.sort(key=lambda c: (-(c.end - c.start), -c.ratio, -c.peso))
    out = []
    for c in cand:
        if all(c.end <= o.start or c.start >= o.end for o in out): out.append(c)
    out.sort(key=lambda c: c.start)
    # «Total efectivo»: el modificador pegado a otra etiqueta se descarta
    i = 0
    while i < len(out) - 1:
        a, b = out[i], out[i + 1]
        if re.fullmatch(r"[\s:.\-|]*", p[a.end:b.start]) and a.campo != b.campo:
            drop = a if a.alias in MODIFICADORES else b if b.alias in MODIFICADORES else None
            if drop: out.remove(drop); continue
        i += 1
    return out


def _analizar(orig: str, V: _Vocab, anio):
    s = norm(orig)
    li = _Li(orig=orig, p="")
    li.dudas, li.ilegible = "[?]" in s, "[ilegible]" in s
    s = s.replace("[?]", "   ").replace("[ilegible]", "         ")
    if "~~" in s:
        li.tachado = True
        s = re.sub(r"~~.*?~~", lambda m: " " * len(m.group(0)), s).replace("~~", "  ")
    s = fix_ocr_digits(words_to_digits(s))
    fecha, s = extraer_fecha(s, anio)
    s = tapar_horas(s)
    li.p = s
    li.labels = _etiquetas(s, V)
    li.amts = find_amounts(s)
    return li, fecha


def _residuo(li: _Li) -> str:
    t = li.p
    for a in sorted(li.amts, key=lambda a: -a.start):
        t = t[:a.start] + " " + t[a.end:]
    return re.sub(r"\s+", " ", re.sub(r"[:=$|\-_.,;()\[\]*#]+", " ", t)).strip()


def _asignar(li: _Li, pref: str):
    p, labs, ams = li.p, li.labels, li.amts
    n = len(labs)
    R = [(labs[i].end, labs[i + 1].start if i + 1 < n else len(p)) for i in range(n)]
    L = [(labs[i - 1].end if i else 0, labs[i].start) for i in range(n)]
    reg = lambda rs: [[a for a in ams if s <= a.start and a.end <= e] for s, e in rs]
    r, l = reg(R), reg(L)
    cr, cl = sum(map(bool, r)), sum(map(bool, l))
    if cr > cl: return r, "der"
    if cl > cr: return l, "izq"
    return (l, "izq") if pref == "izq" else (r, "der")


def parsear(texto: str, config: Config | None = None, anio: int | None = None,
            fuente: str = "", _vocab: _Vocab | None = None) -> Cierre:
    cfg = config or Config()
    V = _vocab or _Vocab(cfg)
    ENT = cfg.esquema.entradas                      # las columnas calculadas no se buscan en la planilla
    CLAVES = [c.clave for c in ENT]
    NOMBRE = {c.clave: c.nombre for c in ENT}; TIPO = {c.clave: c.tipo for c in ENT}; COL = {c.clave: c for c in ENT}
    OPC = cfg.opciones or {}
    anio = anio or cfg.anio
    lines, fecha = [], None
    for raw in texto.splitlines():
        if not raw.strip(): continue
        li, f = _analizar(raw.strip(), V, anio)
        fecha = fecha or f
        li.i = len(lines)
        if f and not li.labels and not li.amts and not re.search(
                r"[a-z]{3,}", re.sub(r"fecha|date|lunes|martes|miercoles|jueves|viernes|sabado|domingo", "", li.p)):
            li.kind = "skip"
        lines.append(li)

    # orientación dominante de la planilla (¿etiqueta→valor o valor→etiqueta?)
    izq = der = 0
    for li in lines:
        if len(li.labels) == 1 and li.amts:
            if any(a.start > li.labels[0].start for a in li.amts): der += 1
            else: izq += 1
    pref = "izq" if izq > der else "der"

    cands = {k: [] for k in CLAVES}
    desc, notas = [], []

    def sv(et, m):
        """Signo del valor. Solo en columnas que admiten negativos (±): «-$138,950» es negativo, y los términos del léxico
        implican su propio signo: FALTANTE/PÉRDIDA → negativo, SOBRANTE/GANANCIA → positivo, aunque no traigan el «-»."""
        if not (et.campo in COL and COL[et.campo].negativo): return m.valor
        s = SIGNO.get(et.alias)
        if m.neg or (s and s[0] < 0): return -abs(m.valor)
        return abs(m.valor)

    def sin_signo(et, m):                            # «Diferencia: 5.000»: ¿falta o sobra?
        s = SIGNO.get(et.alias)
        return bool(et.campo in COL and COL[et.campo].negativo and s and s[2] and not m.neg)

    def cand(et, valor, crudo, li, origen, flags):
        if et.campo not in cands: return              # etiqueta de «ignorar»
        fl = [f for f in flags if f != "suma"]
        if li.dudas: fl.append("dudoso")
        if li.tachado: fl.append("tachado")
        conf = et.peso * et.ratio * ASSOC[origen] * (SIGNO.get(et.alias, (0, 1.0, False))[1] if et.campo in COL and COL[et.campo].negativo else 1.0)
        for f in fl: conf *= PENAL.get(f, 1.0)
        cands[et.campo].append(dict(valor=valor, crudo=crudo, linea=li.orig, conf=round(conf, 3), flags=fl,
                                    alias=et.alias, parte=(et.campo, et.alias) in V.parte, idx=li.i))

    def desconocida(texto_et, m, li):
        texto_et = re.sub(r"\s+", " ", re.sub(r"[:=$|\-_.,;()]+", " ", texto_et)).strip()
        desc.append({"etiqueta": texto_et or "?", "valor": m.valor, "linea": li.orig})

    # 1) líneas con etiqueta(s)
    for li in lines:
        if li.kind == "skip": continue
        if li.labels and li.amts:
            li.kind = "C"
            reg, orient = _asignar(li, pref)
            for et, ams in zip(li.labels, reg):
                if not ams: continue                     # etiqueta sin cifra en una línea con cifras → matiz
                first = ams[0]
                fl = list(first.flags)
                if len(ams) > 1 and any(a.valor != first.valor for a in ams[1:]):
                    fl.append("varios numeros")
                    for a in ams[1:]: desc.append({"etiqueta": "?", "valor": a.valor, "linea": li.orig})
                if sin_signo(et, first): fl.append("signo no indicado (¿faltante o sobrante?)")
                cand(et, sv(et, first), first.texto, li, orient, fl)
        elif li.labels:
            li.kind = "L"
            for i, et in enumerate(li.labels):
                nxt = li.labels[i + 1].start if i + 1 < len(li.labels) else len(li.p)
                tail = li.p[et.end:nxt]
                if li.ilegible and not li.amts:
                    cand(et, None, "[ilegible]", li, "der", ["ilegible"]); continue
                if OPC.get("vacio_cero") and re.fullmatch(r"[\s:=._\-–—]*\$[\s.]*", tail):
                    cand(et, 0, "$", li, "cero", []); continue         # «Total Gastos  $» (sin cifra) = 0
                if re.fullmatch(_CERO, tail):
                    cand(et, 0, tail.strip() or "-", li, "cero", ["cero por guion"]); continue
                li.pend.append(et)
        elif li.amts:
            res = _residuo(li)
            li.kind = "U" if re.search(r"[a-z]{2,}", res) else "A"
        else:
            li.kind = "T" if re.search(r"[a-z]{3,}", li.p) else "skip"

    # 2) cifras en líneas aparte: bloques (columnas / encabezado+fila) y línea siguiente
    N = len(lines)
    usado, resueltas = set(), set()

    def zip_bloque(labs, ams, origen):
        desal = len(labs) != len(ams)
        resueltas.update(id(e) for e in labs)
        for et, a in zip(labs, ams):
            cand(et, sv(et, a), a.texto, lines[a.li], origen, list(a.flags) + (["bloque desalineado"] if desal else []))
        for a in ams[len(labs):]: desc.append({"etiqueta": "?", "valor": a.valor, "linea": lines[a.li].orig})

    def corre(i, k):
        j, out = i, []
        while j < N and lines[j].kind == k:
            out.append(j); j += 1
        return out

    i = 0
    while i < N:
        if lines[i].kind == "L" and lines[i].pend:
            run_l = []
            j = i
            while j < N and lines[j].kind == "L": run_l.append(j); j += 1
            run_a = corre(j, "A")
            labs = [et for x in run_l for et in lines[x].pend]
            if run_a:
                ams = []
                for x in run_a:
                    for a in lines[x].amts: a.li = x; ams.append(a)
                zip_bloque(labs, ams, "sig" if len(labs) == 1 and len(ams) == 1 else "bloque")
                usado.update(run_a)
                i = run_a[-1] + 1; continue
            i = j; continue
        i += 1
    i = 0
    while i < N:                                         # valores arriba, etiquetas abajo
        if lines[i].kind == "A" and i not in usado:
            run_a = []
            j = i
            while j < N and lines[j].kind == "A" and j not in usado: run_a.append(j); j += 1
            run_l, k = [], j
            while k < N and lines[k].kind == "L" and any(id(e) not in resueltas for e in lines[k].pend):
                run_l.append(k); k += 1
            if run_l:
                ams = []
                for x in run_a:
                    for a in lines[x].amts: a.li = x; ams.append(a)
                labs = [et for x in run_l for et in lines[x].pend]
                zip_bloque(labs, ams, "ant")
                usado.update(run_a)
                i = k; continue
            i = j; continue
        i += 1
    for li in lines:                                     # etiquetas que quedaron sin valor
        if li.kind == "L":
            for et in li.pend:
                if id(et) not in resueltas:
                    if et.campo in cands:
                        cands[et.campo].append(dict(valor=None, crudo="", linea=li.orig, conf=0.0, flags=["etiqueta sin valor"],
                                                    alias=et.alias, parte=(et.campo, et.alias) in V.parte, idx=li.i))

    # 3) cifras sueltas, etiquetas desconocidas y notas
    for i, li in enumerate(lines):
        if li.kind == "U":
            prev = 0
            for a in li.amts:
                desconocida(li.p[prev:a.start] or li.p[a.end:], a, li)
                prev = a.end
        elif li.kind == "A" and i not in usado:
            notas.append(f"monto suelto: {li.orig}")
        elif li.kind == "T":
            notas.append(li.orig)

    # 4) elegir el valor de cada campo
    campos, conocidos = {}, []
    for clave in CLAVES:
        c = Campo(clave, NOMBRE[clave])
        cs = cands[clave]
        con = [x for x in cs if x["valor"] is not None]
        gen = [x for x in con if not x["parte"]]
        oc = COL[clave].ocurrencia
        if gen:
            best = max(gen, key=lambda x: x["conf"])
            if oc:                                         # etiqueta repetida: elegir la 1ª, 2ª… o la última aparición
                orden = sorted(gen, key=lambda x: x["idx"])
                if oc == -1 or len(orden) < oc: best = orden[-1]
                else: best = orden[oc - 1]
                if oc > 0 and len(orden) < oc: best = dict(best, flags=best["flags"] + [f"aparece solo {len(orden)} vez(es)"])
            c.valor, c.crudo, c.linea, c.confianza = best["valor"], best["crudo"], best["linea"], best["conf"]
            c.razones = list(best["flags"])
            otros = [] if oc else sorted({x["valor"] for x in gen if x["valor"] != best["valor"]})   # las partes no cuentan como «otro valor»
            if otros:
                c.alternativas = otros; c.razones.append("valores distintos"); c.confianza = round(c.confianza * 0.7, 3)
        elif con:
            partes = {}
            for x in con: partes.setdefault(x["alias"], x)
            c.valor = sum(x["valor"] for x in partes.values())
            c.crudo = " + ".join(x["crudo"] for x in partes.values())
            c.linea = " / ".join(x["linea"] for x in partes.values())
            c.confianza = round(min(x["conf"] for x in partes.values()), 3)
            if len(partes) > 1:
                c.razones = ["suma de partes: " + " + ".join(partes)]; c.confianza = round(c.confianza * 0.9, 3)
            else:
                c.razones = list(next(iter(partes.values()))["flags"])
        elif cs:
            c.linea = cs[0]["linea"]; c.razones = list(dict.fromkeys(f for x in cs for f in x["flags"]))
            c.estado = "revisar"
            campos[clave] = c; continue
        else:
            campos[clave] = c; continue
        c.estado = "ok"
        campos[clave] = c

    # 5) sentido común (no cambia valores; solo marca)
    montos = [c.valor for k, c in campos.items() if TIPO[k] == "monto" and c.valor]
    med = statistics.median(montos) if montos else 0
    for k, c in campos.items():
        if c.valor is None: continue
        if TIPO[k] == "monto" and 0 < c.valor < 1000 and med >= 10000:
            c.razones.append(f"monto muy bajo: ¿{c.valor * 1000:,}?".replace(",", ".")); c.confianza *= PENAL["miles"]
        if TIPO[k] == "conteo" and c.valor > 2000:
            c.razones.append("conteo muy alto"); c.confianza *= PENAL["conteo alto"]
        c.estado = "ok" if (c.confianza >= UMBRAL_OK and not c.razones) else "revisar"

    adv = []
    if not fecha: adv.append("No se encontró la fecha.")
    falt = [NOMBRE[k] for k in CLAVES if campos[k].estado == "faltante"]
    if falt: adv.append("No aparecen: " + ", ".join(falt))
    if cfg.suma_medios and campos["total"].valor is not None:
        s = sum(campos[k].valor or 0 for k in cfg.suma_medios if k in campos)
        if abs(s - campos["total"].valor) > cfg.tolerancia:
            adv.append(f"Los medios de pago suman {s:,} y el total es {campos['total'].valor:,}".replace(",", "."))
    if not OPC.get("notas", True): notas, desc = [], []      # recibos con muchos renglones que no interesan
    return Cierre(fecha, campos, notas, desc, adv, texto, fuente, list(CLAVES), dict(NOMBRE), dict(TIPO))


def montos_del_texto(texto: str) -> set[int]:
    """Todas las cifras presentes en el texto (sirve para validar lo que propone una IA)."""
    V = _Vocab(Config())
    out = set()
    for raw in texto.splitlines():
        if raw.strip():
            li, _ = _analizar(raw.strip(), V, None)
            out.update(a.valor for a in li.amts)
    return out
