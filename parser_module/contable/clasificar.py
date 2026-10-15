"""Clasifica un gasto en una cuenta: 1) lo que tú enseñaste, 2) el proveedor según tu historial, 3) palabras clave."""
from __future__ import annotations
import json, re
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
