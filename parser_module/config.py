"""Configuración del negocio: columnas (esquema) + vocabulario propio que se va ampliando con el uso."""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path
from .esquema import IGNORAR, Esquema, limpiar

PESO_APRENDIDO = 0.95


@dataclass
class Config:
    esquema: Esquema = field(default_factory=Esquema.defecto)
    aliases: dict = None
    partes: dict = None
    suma_medios: list = field(default_factory=list)   # p. ej. ["efectivo","transf","rappi"]: advierte si no suman el total
    tolerancia: int = 1000
    anio: int | None = None
    ruta: str | None = None
    opciones: dict = None
    extra: dict = field(default_factory=dict)          # lo que aporta el usuario (es lo único que se guarda)

    def __post_init__(self):
        if self.opciones is None: self.opciones = self.esquema.opciones
        if self.aliases is None or self.partes is None:
            self.aliases, self.partes = self.esquema.aliases()

    @classmethod
    def cargar(cls, ruta: str | None = None, esquema: Esquema | None = None) -> "Config":
        c = cls(esquema=esquema or Esquema.defecto(), ruta=ruta)
        c.opciones = c.esquema.opciones
        if ruta and Path(ruta).is_file():
            d = json.loads(Path(ruta).read_text(encoding="utf8"))
            for campo, als in (d.get("aliases") or {}).items():
                if campo not in c.esquema.claves: continue            # la columna ya no existe
                items = als.items() if isinstance(als, dict) else [(a, PESO_APRENDIDO) for a in als]
                for a, p in items: c._añadir(campo, a, float(p))
            for campo, als in (d.get("partes") or {}).items():
                if campo in c.esquema.claves:
                    c.partes.setdefault(campo, set()).update(limpiar(a) for a in als)
                    c.extra.setdefault("partes", {}).setdefault(campo, []).extend(als)
            c.suma_medios = d.get("suma_medios", [])
            c.tolerancia = d.get("tolerancia", c.tolerancia)
            c.anio = d.get("anio")
        return c

    def _añadir(self, campo: str, alias: str, peso: float):
        if campo not in [x.clave for x in self.esquema.entradas]:
            raise ValueError(f"Columna desconocida '{campo}'. Usa una de: {', '.join(self.esquema.claves)}")
        a = limpiar(alias)
        if not a:
            return
        self.aliases.setdefault(campo, {})[a] = peso
        self.extra.setdefault("aliases", {}).setdefault(campo, {})[a] = peso

    def aprender(self, alias: str, campo: str, peso: float = PESO_APRENDIDO):
        """Enseña una etiqueta nueva (p. ej. 'gas' → cajam) y la guarda."""
        self._añadir(campo, alias, peso)
        self.guardar()

    def guardar(self, ruta: str | None = None):
        ruta = ruta or self.ruta
        if not ruta:
            return
        d = dict(self.extra)
        if self.suma_medios:
            d["suma_medios"] = self.suma_medios
            d["tolerancia"] = self.tolerancia
        if self.anio:
            d["anio"] = self.anio
        Path(ruta).write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf8")
        self.ruta = ruta
