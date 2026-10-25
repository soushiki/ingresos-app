"""Clasifica un gasto en una cuenta: 1) lo que tú enseñaste, 2) el proveedor según tu historial, 3) palabras clave."""
from __future__ import annotations
import json, re
from difflib import SequenceMatcher
from pathlib import Path
from ..numeros import norm

AQUI = Path(__file__).parent
_PESO_DUDOSO = 0.6
# cuenta → palabras (raíces) · («raíz», peso) si la palabra es ambigua
LEXICO = {
    "14050501": ["carne", "res", "pollo", "cerdo", "pescado", "camaron", "verdura", "papa", "tomate", "cebolla", "harina", "aceite", "queso", "huevo",
                 "pan", "arroz", "frijol", "salsa", "lacteo", "platano", "yuca", "aguacate", "ajo", "mantequilla", "tocino", "embutido", "chorizo"],
    "14050502": ["cerveza", "heineken", "aguila", "club", "gaseosa", "jugo", "licor", "ron", "aguardiente", "whisky", "vodka", "hielo", "tonica",
                 "postobon", "pepsi", "energizante", "vino", "botella"],
    "14050503": ["empaque", "desechable", "icopor", "pitillo", "contenedor", "cubierto", "vaso", "tapa"],
    "28150501": ["domicilio", "domiciliario"],
    "51355001": ["transporte", "flete", "acarreo", "taxi", "bus", "uber", "moto", "mudanza", "pasaje"],
    "51952501": ["aseo", "limpieza", "jabon", "detergente", "cloro", "escoba", "trapero", "esponja", "basura", "desinfectante", "cafe", "azucar",
                 "servilleta", "ambientador", "trapo", "lavaplatos", "fabuloso"],
    "51953001": ["papel", "papeleria", "fotocopia", "resma", "tinta", "impresion", "marcador", "cartulina", "toner", "sticker", "etiqueta"],
    "51957501": [("pila", _PESO_DUDOSO), "herramienta", "destornillador", "martillo", "taladro", "alicate", "candado", "cinta", "bateria"],
    "51501501": ["reparacion", "arreglo", "plomer", "pintura", "pintor", "cerradura", "cerrajer", "albanil", "soldadura", "tuberia"],
    "51451504": ["extintor", "recarga"],
    "51353001": ["energia", "afinia", "electricaribe"], "51353002": ["gas", "pipeta", "surtigas"],
    "51353003": ["internet"], "51353004": ["telefono", "movistar", "celular", "minutos", "claro"],
    "51352501": ["acueducto", "alcantarillado", "acuacar"],
    "51050601": ["nomina", "sueldo", "quincena", "salario", "turno"], "51055101": ["dotacion", "uniforme", "delantal"],
    "52356001": ["publicidad", "volante", "pendon", "valla", "pauta", "promocion"], "51401501": ["tramite", "licencia", "sayco", "acinpro", "camara de comercio"],
    "53050502": ["bancario", "cuota de manejo"], "51953501": ["gasolina", "combustible", "acpm"], "51957001": ["celebracion", "evento", "decoracion"],
    "13301501": ["adelanto", "anticipo"], "52950501": ["comision"],
}
LEXICO["14050503"] += ["salsero", "recipiente", "kraft"]          # empaques y envases
LEXICO["14050501"] += ["leche", "panes", "hamburguesa"]          # insumos de cocina
FRASES = {"papel higienico": "51952501", "papel aluminio": "14050503", "papel vinipel": "14050503", "gas natural": "51353002"}
GENERICOS = {"consumidor final", "cuantias menores", "caja", ""}


def _toks(s): return re.findall(r"[a-z]{2,}", norm(s))


class Clasificador:
    def __init__(self, ruta_aprendido: str | None = None):
        self.ruta = Path(ruta_aprendido) if ruta_aprendido else None
        archivo = AQUI / "terceros_cuentas.json"
        if not archivo.is_file(): archivo = AQUI / "terceros_cuentas.example.json"   # el real no se versiona
        self.terceros = json.loads(archivo.read_text(encoding="utf8"))
        self.aprendido = {"terceros": {}, "detalles": {}}
        if self.ruta and self.ruta.is_file():
            try: self.aprendido.update(json.loads(self.ruta.read_text(encoding="utf8")))
            except json.JSONDecodeError: pass

    def aprender(self, cuenta: str, tercero: str = "", detalle: str = ""):
        t, d = norm(tercero).strip(), " ".join(_toks(detalle))
        if t and t not in GENERICOS: self.aprendido["terceros"][t] = cuenta
        elif d: self.aprendido["detalles"][d] = cuenta
        if self.ruta: self.ruta.write_text(json.dumps(self.aprendido, ensure_ascii=False, indent=1), encoding="utf8")

    def clasificar(self, tercero: str = "", detalle: str = "", texto: str = "") -> dict:
        t = norm(tercero).strip(); d = " ".join(_toks(detalle))
        if t and t not in GENERICOS and t in self.aprendido["terceros"]: return dict(cuenta=self.aprendido["terceros"][t], conf=0.98, motivo="lo enseñaste para este proveedor")
        if d and d in self.aprendido["detalles"]: return dict(cuenta=self.aprendido["detalles"][d], conf=0.98, motivo="lo enseñaste para esta descripción")
        if t and t not in GENERICOS and t in self.terceros: return dict(cuenta=self.terceros[t]["cuenta"], conf=0.9, motivo=f"tu historial: {self.terceros[t]['n']} veces con este proveedor")
        base = norm(" ".join([detalle, tercero] if detalle or tercero else [texto]))
        for f, c in FRASES.items():
            if f in base: return dict(cuenta=c, conf=0.85, motivo=f"«{f}»")
        toks = _toks(base); puntos = {}
        for cuenta, kws in LEXICO.items():
            for kw in kws:
                k, w = (kw, 1.0) if isinstance(kw, str) else kw
                hit = (k in base) if " " in k else any(x == k or (len(k) >= 4 and x.startswith(k)) for x in toks)   # raíces cortas solo exactas («sal» no es «salsero»)
                if hit: puntos.setdefault(cuenta, []).append((k, w))
        if not puntos: return dict(cuenta="", conf=0.0, motivo="sin palabras conocidas")
        ranking = sorted(puntos.items(), key=lambda kv: -sum(w for _, w in kv[1]))
        mejor, hits = ranking[0]
        conf = 0.85 if all(w == 1.0 for _, w in hits) else _PESO_DUDOSO
        if len(ranking) > 1 and sum(w for _, w in ranking[1][1]) == sum(w for _, w in hits): conf = min(conf, 0.5)   # empate entre cuentas
        return dict(cuenta=mejor, conf=conf, motivo="palabras: " + ", ".join(k for k, _ in hits))


# ── Motor por capas (M-27, ADR-020) ──────────────────────────────────────────────────────────────────────────────────────────────────────────────
# Fuentes de las cuentas (regulated): origen → R1 (41401501 ingresos de restaurante, plan de cuentas del negocio); LEXICO/FRASES → a mano;
# minado/proveedor/vecino → el cuadro manual del contador (jun–oct, `modelo_manual.json`); puente → cuenta del contador para «gasto sin cuenta»
# (asientos.CFG["puente_gasto"]). La validación contra el PUC (Decreto 2650/1993) la añade `puc_valida` (T4, ADR-022).

PUENTE_GASTO = "51959501"            # = asientos.CFG["puente_gasto"]
ORIGEN = {"venta": "41401501", "rappi": "41401501", "cierre": "41401501"}   # R1: la comanda fija el ingreso; la contrapartida va por medio (asientos)
UMBRALES = {"vecino": 0.75, "empate": 0.05, "candidatos": 20}               # ADR-020; se pueden pisar en confirmar["umbrales"]


def _tri(s: str) -> set:
    s = f"  {s} "; return {s[i:i + 3] for i in range(len(s) - 2)}


class Motor:
    """Clasifica un ítem en capas de orden fijo y dice cuál decidió. Es puro: recibe el modelo minado, «confirmar» y lo enseñado como dicts."""

    def __init__(self, modelo: dict, confirmar: dict | None = None, aprendido: dict | None = None):
        self.modelo = {"lexico": {}, "proveedores": {}, "vecinos": []} | (modelo or {})
        self.confirmar = confirmar or {}
        self.aprendido = {"terceros": {}, "detalles": {}} | (aprendido or {})
        self.umbral = UMBRALES | self.confirmar.get("umbrales", {})
        self.puente = self.confirmar.get("puentes", {}).get("gasto") or PUENTE_GASTO
        self.provs = {norm(k).strip(): v for k, v in self.modelo["proveedores"].items()}
        self.indice = {}                                         # trigrama → posiciones en vecinos
        for i, v in enumerate(self.modelo["vecinos"]):
            for t in _tri(v["texto"]): self.indice.setdefault(t, []).append(i)

    @classmethod
    def desde_archivos(cls, ruta_aprendido: str | None = None, ruta_modelo: str | None = None) -> "Motor":
        modelo = json.loads(Path(ruta_modelo or AQUI / "modelo_manual.json").read_text(encoding="utf8"))
        conf = AQUI / "por_confirmar.json"
        confirmar = json.loads(conf.read_text(encoding="utf8")) if conf.is_file() else {}
        aprendido = {}
        if ruta_aprendido and Path(ruta_aprendido).is_file():
            try: aprendido = json.loads(Path(ruta_aprendido).read_text(encoding="utf8"))
            except json.JSONDecodeError: pass
        return cls(modelo, confirmar, aprendido)

    def _sale(self, cuenta, conf, capa, motivo): return dict(cuenta=cuenta, conf=round(conf, 2), capa=capa, motivo=motivo)

    def clasificar_item(self, origen: str, nombre: str, tercero: str = "", texto: str = "") -> dict:
        """origen: venta · rappi · cierre · gasto · factura … ; nombre: el ítem (o el detalle del papel). → {cuenta, conf, capa, motivo}."""
        if origen in ORIGEN: return self._sale(ORIGEN[origen], 1.0, "origen", "origen: comanda")
        toks = _toks(nombre or texto); d = " ".join(toks); t = norm(tercero).strip()
        if d and d in self.aprendido["detalles"]: return self._sale(self.aprendido["detalles"][d], 0.98, "enseñado", "lo enseñaste para esta descripción")
        if t and t not in GENERICOS and t in self.aprendido["terceros"]: return self._sale(self.aprendido["terceros"][t], 0.98, "enseñado", "lo enseñaste para este proveedor")
        base = norm(nombre or texto)
        for f, c in FRASES.items():
            if f in base: return self._sale(c, 0.9, "frase", f"«{f}»")
        puntos = {}
        for cuenta, kws in LEXICO.items():
            for kw in kws:
                k, w = (kw, 1.0) if isinstance(kw, str) else kw
                if (k in base) if " " in k else any(x == k or (len(k) >= 4 and x.startswith(k)) for x in toks): puntos.setdefault(cuenta, []).append((k, w))
        if puntos:
            rk = sorted(puntos.items(), key=lambda kv: -sum(w for _, w in kv[1]))
            if len(rk) == 1 or sum(w for _, w in rk[1][1]) < sum(w for _, w in rk[0][1]):   # empate entre cuentas: no decide, siguen las capas
                hits = rk[0][1]
                return self._sale(rk[0][0], 0.85 if all(w == 1.0 for _, w in hits) else _PESO_DUDOSO, "lexico", "palabras: " + ", ".join(k for k, _ in hits))
        votos = {}
        for x in toks:
            e = self.modelo["lexico"].get(x)
            if e: votos.setdefault(e["cuenta"], []).append((x, e))
        if votos:
            rk = sorted(votos.items(), key=lambda kv: -sum(e["n"] for _, e in kv[1]))
            if len(rk) == 1 or sum(e["n"] for _, e in rk[1][1]) < sum(e["n"] for _, e in rk[0][1]):
                c, hits = rk[0]
                return self._sale(c, min(0.9, min(e["n"] / e["de"] for _, e in hits)), "minado",
                                  "manual: " + ", ".join(f"«{x}» {e['n']} de {e['de']}" for x, e in hits))
        if t and t not in GENERICOS and t in self.provs:
            e = self.provs[t]; return self._sale(e["cuenta"], min(0.9, e["n"] / e["de"]), "proveedor", f"manual: proveedor {e['n']} de {e['de']} veces")
        if d:
            cand = {}
            for t3 in _tri(d):
                for i in self.indice.get(t3, ()): cand[i] = cand.get(i, 0) + 1
            top = sorted(cand, key=lambda i: -cand[i])[: self.umbral["candidatos"]]
            vs = self.modelo["vecinos"]
            mejores = sorted(((SequenceMatcher(None, d, vs[i]["texto"]).ratio(), i) for i in top), reverse=True)
            if mejores and mejores[0][0] >= self.umbral["vecino"]:
                r1, i1 = mejores[0]
                otro = next(((r, i) for r, i in mejores[1:] if vs[i]["cuenta"] != vs[i1]["cuenta"]), None)
                if otro and r1 - otro[0] < self.umbral["empate"]:
                    return self._sale(self.puente, 0.0, "puente", f"empate: {vs[i1]['cuenta']} («{vs[i1]['texto']}») y {vs[otro[1]]['cuenta']} («{vs[otro[1]]['texto']}»)")
                return self._sale(vs[i1]["cuenta"], r1, "vecino", f"parecido a {vs[i1]['fuente']} («{vs[i1]['texto']}»)")
        return self._sale(self.puente, 0.0, "puente", "sin palabras conocidas")
