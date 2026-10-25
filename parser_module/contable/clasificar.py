"""Clasifica un gasto en una cuenta: 1) lo que tú enseñaste, 2) el proveedor según tu historial, 3) palabras clave."""
from __future__ import annotations
import json, re
from difflib import SequenceMatcher
from pathlib import Path
from ..numeros import norm
from .puc import puc_valida
from .asientos import CFG as _CFG_ASIENTOS
from .documentos import items_de

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
FRASES = {"papel higienico": "51952501", "papel aluminio": "14050503", "papel vinipel": "14050503", "gas natural": "51353002",
          "pago de compras": "14050501"}    # ADR-023: cuenta de mayoría del manual («pago compra» 5 de 6)
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
# Fuentes de las cuentas (regulated): origen → R1 (`por_confirmar.json` «origen», con su fuente); LEXICO/FRASES → a mano;
# minado/proveedor/vecino → el cuadro manual del contador (jun–oct, `modelo_manual.json`); puente → cuenta del contador para «gasto sin cuenta»
# (asientos.CFG["puente_gasto"], que pisa contable.json). La validación contra el PUC (Decreto 2650/1993) la hace `puc_valida` (T4, ADR-022)
# sobre toda salida que no sea la puente, también la minada (así el alias reescribe los códigos viejos del manual); solo lo que el usuario
# puso a mano (`manual=`) no se cambia, solo se avisa. ADR-022: ningún código de 8 dígitos fuera de LEXICO/FRASES vive aquí.

PUENTE_GASTO = _CFG_ASIENTOS["puente_gasto"]
_PC = AQUI / "por_confirmar.json"
CONFIRMAR = json.loads(_PC.read_text(encoding="utf8")) if _PC.is_file() else {}
ORIGEN = CONFIRMAR.get("origen", {})      # R1: la comanda fija el ingreso; la contrapartida va por medio (asientos)
UMBRALES = {"vecino": 0.75, "empate": 0.05, "candidatos": 20}               # ADR-020; se pueden pisar en confirmar["umbrales"]


def _tri(s: str) -> set:
    s = f"  {s} "; return {s[i:i + 3] for i in range(len(s) - 2)}


class Motor:
    """Clasifica un ítem en capas de orden fijo y dice cuál decidió. Es puro: recibe el modelo minado, «confirmar» y lo enseñado como dicts."""

    def __init__(self, modelo: dict, confirmar: dict | None = None, aprendido: dict | None = None, terceros: dict | None = None):
        self.modelo = {"lexico": {}, "bigramas": {}, "proveedores": {}, "vecinos": []} | (modelo or {})
        self.confirmar = confirmar or {}
        self.aprendido = {"terceros": {}, "detalles": {}} | (aprendido or {})
        self.umbral = UMBRALES | self.confirmar.get("umbrales", {})
        self.puente = self.confirmar.get("puentes", {}).get("gasto") or PUENTE_GASTO
        self.alias, self.notas = self.confirmar.get("alias", {}), self.confirmar.get("alias_nota", {})
        self.origen = self.confirmar.get("origen") or ORIGEN
        self.provs = {norm(k).strip(): dict(v, de=v.get("de", v["n"])) for k, v in (self.modelo["proveedores"] | (terceros or {})).items()}   # + personas (local, N5)
        self.choque = [d for d in self.confirmar.get("decisiones", []) if d.get("motor") and d.get("estado") == "por confirmar" and d.get("cuenta")]   # ADR-023
        self.indice = {}                                         # trigrama → posiciones en vecinos
        for i, v in enumerate(self.modelo["vecinos"]):
            for t in _tri(v["texto"]): self.indice.setdefault(t, []).append(i)

    @classmethod
    def desde_archivos(cls, ruta_aprendido: str | None = None, ruta_modelo: str | None = None) -> "Motor":
        modelo = json.loads(Path(ruta_modelo or AQUI / "modelo_manual.json").read_text(encoding="utf8"))
        confirmar = json.loads(_PC.read_text(encoding="utf8")) if _PC.is_file() else {}
        aprendido = {}
        if ruta_aprendido and Path(ruta_aprendido).is_file():
            try: aprendido = json.loads(Path(ruta_aprendido).read_text(encoding="utf8"))
            except json.JSONDecodeError: pass
        archivo = AQUI / "terceros_cuentas.json"
        if not archivo.is_file(): archivo = AQUI / "terceros_cuentas.example.json"      # el real no se versiona
        terceros = json.loads(archivo.read_text(encoding="utf8")) if archivo.is_file() else {}
        return cls(modelo, confirmar, aprendido, terceros)

    def _sale(self, cuenta, conf, capa, motivo): return dict(cuenta=cuenta, conf=round(conf, 2), capa=capa, motivo=motivo)

    def clasificar_item(self, origen: str, nombre: str, tercero: str = "", texto: str = "", manual: str = "") -> dict:
        """origen: venta · rappi · cierre · gasto · factura … ; nombre: el ítem (o el detalle del papel). → {cuenta, conf, capa, motivo}.
        manual: la cuenta que el usuario puso a mano (T9); se respeta y solo se avisa.
        Último paso `puc_valida` (ADR-022) para toda salida menos la puente: alias manual→PUC y `revisar`; lo que no sea «ok»/«propia» va a la puente."""
        if manual:
            m = str(manual).strip(); _, _, aviso = puc_valida(m, self.alias, self.notas)
            return self._sale(m, 1.0, "manual", "lo pusiste a mano" + (f" · aviso PUC: {aviso}" if aviso else ""))
        r = self._decidir(origen, nombre, tercero, texto)
        if r["capa"] == "puente": return r
        cuenta, estado, aviso = puc_valida(r["cuenta"], self.alias, self.notas)
        if estado not in ("ok", "propia"): return self._sale(self.puente, 0.0, "puente", f"{r['cuenta']} fuera del PUC ({estado}); {r['motivo']}")
        return dict(r, cuenta=cuenta, motivo=f"{r['motivo']} · {aviso}" if aviso else r["motivo"])

    def _decidir(self, origen: str, nombre: str, tercero: str = "", texto: str = "") -> dict:
        if origen in self.origen: return self._sale(self.origen[origen], 1.0, "origen", "origen: comanda")
        toks = _toks(nombre or texto); d = " ".join(toks); t = norm(tercero).strip()
        if d and d in self.aprendido["detalles"]: return self._sale(self.aprendido["detalles"][d], 0.98, "enseñado", "lo enseñaste para esta descripción")
        if t and t not in GENERICOS and t in self.aprendido["terceros"]: return self._sale(self.aprendido["terceros"][t], 0.98, "enseñado", "lo enseñaste para este proveedor")
        for dec in self.choque:       # ADR-023: palabras de una decisión que choca en el manual; sale la cuenta de mayoría, avisada
            if any(x in set(dec["afecta"]) for x in toks): return self._sale(dec["cuenta"], 0.75, "confirmar", f"por confirmar: {dec['regla_usada']}")
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
        w3 = re.findall(r"[a-z]{3,20}", base); par = [f"{a} {b}" for a, b in zip(w3, w3[1:])]    # bigramas del minado (≥ 2 veces, ≥ 80 %)
        hb = [(p, self.modelo["bigramas"][p]) for p in par if p in self.modelo["bigramas"]]
        if hb:
            rk = {}
            for p, e in hb: rk.setdefault(e["cuenta"], []).append((p, e))
            rk = sorted(rk.items(), key=lambda kv: -sum(e["n"] for _, e in kv[1]))
            if len(rk) == 1 or sum(e["n"] for _, e in rk[1][1]) < sum(e["n"] for _, e in rk[0][1]):
                c, hits = rk[0]
                return self._sale(c, min(0.9, min(e["n"] / e["de"] for _, e in hits)), "minado", "manual: " + ", ".join(f"«{p}» {e['n']} de {e['de']}" for p, e in hits))
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

    # T8 (R1, R5): el papel entero. Ventas, Rappi y cierre: la comanda fija el ingreso (origen), sus `items` son líneas de plato y no se tocan.
    # Compras (factura, gasto de caja, caja menor): cada ítem de items_de(doc) pasa por clasificar_item; doc.cuenta = la del ítem de mayor valor.
    def clasificar_doc(self, doc: dict) -> dict:
        """Llena items[].cuenta/conf/capa/motivo y fija doc.cuenta/conf/motivo. Idempotente: un ítem ya decidido (con capa) o heredado de un papel
        viejo (cuenta sin capa) no se vuelve a clasificar (reclasificar es T10); el `manual` se respeta siempre. doc.cuenta queda "" si el
        ítem mayor fue a la puente, para que siga el aviso «falta cuenta» (los ítems sí llevan el código de la puente)."""
        tipo = doc.get("tipo")
        if tipo in ("venta", "cierre"):
            if doc.get("cuenta"): return doc                  # ya clasificado, o lo puso el usuario
            r = self.clasificar_item("rappi" if doc.get("rappi") else tipo, "")
            doc["cuenta"], doc["conf"], doc["motivo"] = r["cuenta"], r["conf"], r["motivo"]
            return doc
        if tipo not in ("factura", "gasto_caja", "caja_menor_manuscrito"): return doc
        a_mano = str(doc["cuenta"]) if doc.get("cuenta_manual") and doc.get("cuenta") else ""   # FIX-1: la cuenta que el usuario eligió en la tarjeta
        # FIX-2 (06 #4): si cambió el tipo, el tercero, el detalle o el valor desde la última pasada, los ítems no manuales se rehacen
        huella = [tipo, doc.get("tercero") or "", doc.get("detalle") or "", doc.get("valor") or doc.get("consumo") or 0]
        if doc.get("items_huella") not in (None, huella) and doc.get("items") and not a_mano and not any(i.get("manual") for i in doc["items"]):
            doc["items"] = []; doc["cuenta"] = ""
        doc["items_huella"] = huella
        its = items_de(doc); origen = "factura" if tipo == "factura" else "gasto"
        for it in its:
            if a_mano and not it.get("manual"): it["manual"] = a_mano
            if it.get("manual"): r = self.clasificar_item(origen, it.get("nombre", ""), manual=it["manual"])
            elif it.get("capa") not in (None, "", "puente") or (it.get("cuenta") and not it.get("capa")): continue   # FIX-2 (06 #3): la puente se reclasifica en cada pasada
            else: r = self.clasificar_item(origen, it.get("nombre", ""), doc.get("tercero", ""), doc.get("texto", "") if len(its) == 1 else "")
            it.update(cuenta=r["cuenta"], conf=r["conf"], capa=r["capa"], motivo=r["motivo"])
        doc["items"] = its
        top = max(its, key=lambda i: int(i.get("valor") or 0))
        if a_mano: doc["conf"], doc["motivo"] = 1.0, its[0].get("motivo", "") if len(its) == 1 else "lo pusiste a mano"; return doc
        doc["cuenta"] = "" if top.get("capa") == "puente" else top["cuenta"]
        doc["conf"], doc["motivo"] = top.get("conf", 0.0), top.get("motivo", "")
        return doc
