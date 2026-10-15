"""Esquema de columnas definido por el usuario: nombres, tipo, sinónimos, fórmulas y controles, ANTES de analizar las imágenes."""
from __future__ import annotations
import json, re
from dataclasses import dataclass, field
from pathlib import Path
from .campos import ALIAS_BASE, CAMPOS, NOMBRE as NOMBRE_BASE, PARTES_BASE
from .formulas import claves_de, validar
from .numeros import norm

MAX_COLUMNAS = 40
TIPOS = ("monto", "conteo", "calculo")   # monto = dinero · conteo = cantidad · calculo = fórmula entre otras columnas
OPCIONES_BASE = {"vacio_cero": False, "notas": True}
IGNORAR = "__ignorar__"


def limpiar(s) -> str:
    """minúsculas, sin tildes ni signos (conserva '#')."""
    return " ".join(re.sub(r"[^a-z0-9#]+", " ", norm(str(s))).split())


def _variantes(n: str) -> set:
    out = {n}
    if n.endswith("s") and len(n) > 4: out.add(n[:-1])
    elif n and not n.endswith("s"): out.add(n + "s")
    return out


@dataclass
class Columna:
    clave: str
    nombre: str
    tipo: str = "monto"
    sinonimos: list = field(default_factory=list)
    formula: str = ""          # solo tipo «calculo»; internamente con {clave}
    negativo: bool = False     # admite «-$138,950»
    ocurrencia: int = 0        # etiqueta repetida: 0 = la mejor · 1,2,3 = esa aparición · -1 = la última
    resultado: bool = False    # columna de ganancia(+)/pérdida(−): se resume y se pinta en verde/rojo
    partes: list = field(default_factory=list)   # sinónimos con «+»: son PARTES (p. ej. crédito + débito); se suman si no aparece el total


@dataclass
class Esquema:
    columnas: list
    controles: list = field(default_factory=list)   # [{"nombre","formula"({clave}),"tolerancia"}] → fórmula que debe dar ≈ 0
    ignorar: list = field(default_factory=list)     # etiquetas que se descartan en silencio
    opciones: dict = field(default_factory=lambda: dict(OPCIONES_BASE))

    claves = property(lambda s: [c.clave for c in s.columnas])
    nombres = property(lambda s: {c.clave: c.nombre for c in s.columnas})
    tipos = property(lambda s: {c.clave: c.tipo for c in s.columnas})
    entradas = property(lambda s: [c for c in s.columnas if c.tipo != "calculo"])
    calculadas = property(lambda s: [c for c in s.columnas if c.tipo == "calculo"])

    # ── construcción ──
    @classmethod
    def defecto(cls) -> "Esquema":
        return cls([Columna(k, n, t) for k, n, t in CAMPOS])

    @classmethod
    def plantilla(cls, nombre: str) -> "Esquema":
        from .plantillas import PLANTILLAS
        return cls.desde_dict(PLANTILLAS[nombre][1]())

    @classmethod
    def desde_lista(cls, lista) -> "Esquema":
        return cls.desde_dict({"columnas": lista})

    @classmethod
    def desde_dict(cls, d) -> "Esquema":
        """Valida lo que envía el usuario. Lanza ValueError con un mensaje claro."""
        lista = (d or {}).get("columnas")
        if not isinstance(lista, list) or not lista: raise ValueError("Define al menos una columna.")
        if len(lista) > MAX_COLUMNAS: raise ValueError(f"Máximo {MAX_COLUMNAS} columnas.")
        cols, usadas, vistos, lns = [], set(), set(), []
        for it in lista:
            nombre = " ".join(str(it.get("nombre", "")).split())[:40]
            if not nombre: raise ValueError("Hay una columna sin nombre.")
            ln = limpiar(nombre)
            if not ln: raise ValueError(f"El nombre «{nombre}» no es válido.")
            if ln in vistos: raise ValueError(f"Dos columnas se llaman «{nombre}».")
            vistos.add(ln)
            tipo = it.get("tipo") if it.get("tipo") in TIPOS else "monto"
            sin = it.get("sinonimos") or []
            if isinstance(sin, str): sin = re.split(r"[,\n;]", sin)
            sin = [] if tipo == "calculo" else list(dict.fromkeys(s.strip() for s in map(str, sin) if limpiar(s)))
            prt = [s.lstrip("+ ").strip() for s in sin if s.startswith("+") and limpiar(s)][:20]
            sin = [s for s in sin if not s.startswith("+") and limpiar(s) != ln][:40]
            clave = str(it.get("clave") or "")
            if re.fullmatch(r"[a-z][a-z0-9_]{0,30}", clave) and clave not in usadas: usadas.add(clave)
            else: clave = ""
            oc = it.get("ocurrencia", 0)
            oc = oc if isinstance(oc, int) and -1 <= oc <= 9 else 0
            cols.append(Columna(clave, nombre, tipo, sin, str(it.get("formula") or "").strip(),
                                bool(it.get("negativo")), oc, bool(it.get("resultado")) and tipo == "calculo", prt))
            lns.append(ln)
        for c, ln in zip(cols, lns):            # claves nuevas: reutiliza el vocabulario original si coincide
            if c.clave: continue
            if c.tipo != "calculo":
                for k in NOMBRE_BASE:
                    if k not in usadas and (ln == limpiar(NOMBRE_BASE[k]) or
                                            ln in {limpiar(a) for a, p in ALIAS_BASE[k].items() if p >= 1}):
                        c.clave = k; break
            if not c.clave:
                base = re.sub(r"[^a-z0-9]+", "_", ln).strip("_")[:24] or "col"
                if not base[0].isalpha(): base = "c_" + base
                c.clave, i = base, 2
                while c.clave in usadas: c.clave = f"{base}_{i}"; i += 1
            usadas.add(c.clave)
        por_nombre = {limpiar(c.nombre): c.clave for c in cols}

        def a_claves(f, donde):                 # [Nombre] → {clave}
            def rep(m):
                k = por_nombre.get(limpiar(m.group(1)))
                if not k: raise ValueError(f"{donde}: no existe la columna «{m.group(1)}».")
                return "{" + k + "}"
            return re.sub(r"\[([^\]]+)\]", rep, f)

        for c in cols:
            if c.tipo == "calculo":
                if not c.formula: raise ValueError(f"La columna calculada «{c.nombre}» necesita una fórmula.")
                c.formula = a_claves(c.formula, f"Fórmula de «{c.nombre}»")
                validar(c.formula, set(usadas) - {c.clave})
        _sin_ciclos(cols)
        ctrls = []
        for it in (d.get("controles") or []):
            nm, f = " ".join(str(it.get("nombre", "")).split())[:90], str(it.get("formula") or "").strip()
            if not f: continue
            f = a_claves(f, f"Control «{nm or '?'}»"); validar(f, usadas)
            try: tol = max(0, float(it.get("tolerancia", 1)))
            except (TypeError, ValueError): tol = 1
            ctrls.append({"nombre": nm or "Control", "formula": f, "tolerancia": tol})
        ign = list(dict.fromkeys(limpiar(a) for a in (d.get("ignorar") or []) if limpiar(a)))
        op = dict(OPCIONES_BASE); op.update({k: bool(v) for k, v in (d.get("opciones") or {}).items() if k in OPCIONES_BASE})
        esq = cls(cols, ctrls, ign, op)
        esq.aliases()                                   # valida choques de sinónimos
        return esq

    @classmethod
    def cargar(cls, ruta, por_defecto: "Esquema | None" = None) -> "Esquema":
        try:
            return cls.desde_dict(json.loads(Path(ruta).read_text(encoding="utf8")))
        except (FileNotFoundError, ValueError, KeyError, json.JSONDecodeError, TypeError):
            return por_defecto or cls.defecto()

    def guardar(self, ruta):
        Path(ruta).write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=1), encoding="utf8")

    # ── salida ──
    def _nombres_en(self, f: str) -> str:           # {clave} → [Nombre]
        n = self.nombres
        return re.sub(r"\{([a-z][a-z0-9_]*)\}", lambda m: f"[{n.get(m.group(1), m.group(1))}]", f or "")

    def to_dict(self, ui: bool = False) -> dict:
        cols = []
        for c in self.columnas:
            d = {"clave": c.clave, "nombre": c.nombre, "tipo": c.tipo, "sinonimos": list(c.sinonimos),
                 "negativo": c.negativo, "ocurrencia": c.ocurrencia, "resultado": c.resultado,
                 "formula": self._nombres_en(c.formula)}
            d["sinonimos"] = list(c.sinonimos) + ["+" + p for p in c.partes]
            if ui: d["formula_k"] = c.formula
            cols.append(d)
        ctr = [{"nombre": x["nombre"], "formula": self._nombres_en(x["formula"]), "tolerancia": x["tolerancia"],
                **({"formula_k": x["formula"]} if ui else {})} for x in self.controles]
        return {"columnas": cols, "controles": ctr, "ignorar": list(self.ignorar), "opciones": dict(self.opciones)}

    def to_list(self):
        return self.to_dict()["columnas"]

    # ── cálculo ──
    def evaluar(self, valores: dict) -> dict:
        """Valores de entrada → {clave: valor} incluyendo las columnas calculadas (en orden de dependencia)."""
        from .formulas import evaluar
        out = dict(valores)
        pend = list(self.calculadas)
        for _ in range(len(pend) + 1):
            for c in list(pend):
                if all(k in out or k not in {x.clave for x in pend} for k in claves_de(c.formula)):
                    out[c.clave] = round(evaluar(c.formula, out), 2); pend.remove(c)
        return out

    def controlar(self, valores: dict) -> list:
        """→ lista de controles que NO cuadran: [{"nombre","diferencia","claves"}]."""
        from .formulas import evaluar
        todo = self.evaluar(valores); fallan = []
        for x in self.controles:
            dif = evaluar(x["formula"], todo)
            if abs(dif) > x["tolerancia"]:
                fallan.append({"nombre": x["nombre"], "diferencia": round(dif, 2), "claves": claves_de(x["formula"])})
        return fallan

    def aliases(self):
        """→ ({clave: {alias: peso}}, {clave: {alias de 'parte'}}). Lo que escribe el usuario manda; el vocabulario base completa."""
        ent = self.entradas
        dueño, out, nom = {}, {c.clave: {} for c in ent}, self.nombres
        out[IGNORAR] = {}

        def poner(clave, alias, peso, estricto):
            if not alias: return
            o = dueño.get(alias)
            if o is None: dueño[alias] = clave; out[clave][alias] = peso
            elif o != clave and estricto:
                raise ValueError(f"«{alias}» está repetido en las columnas «{nom.get(o, 'ignorar')}» y «{nom.get(clave, 'ignorar')}».")

        for c in ent:
            poner(c.clave, limpiar(c.nombre), 1.0, True)
            for s in c.sinonimos: poner(c.clave, limpiar(s), 0.95, True)
        for a in self.ignorar: poner(IGNORAR, a, 1.0, False)
        partes_c = {}
        for c in ent:
            for p in c.partes:
                poner(c.clave, limpiar(p), 0.9, True); partes_c.setdefault(c.clave, set()).add(limpiar(p))
        for c in ent:
            for v in _variantes(limpiar(c.nombre)): poner(c.clave, v, 0.95, False)
        for c in ent:
            for a, p in ALIAS_BASE.get(c.clave, {}).items(): poner(c.clave, a, p, False)
        partes = {k: set(v) for k, v in PARTES_BASE.items() if k in out}
        for k, v in partes_c.items(): partes.setdefault(k, set()).update(v)
        return out, partes


def _sin_ciclos(cols):
    deps = {c.clave: set(claves_de(c.formula)) for c in cols if c.tipo == "calculo"}
    estado = {}
    def visita(k, ruta):
        if estado.get(k) == 2 or k not in deps: return
        if estado.get(k) == 1: raise ValueError("Las fórmulas se refieren unas a otras en círculo.")
        estado[k] = 1
        for d in deps[k]: visita(d, ruta)
        estado[k] = 2
    for k in deps: visita(k, [])
