"""Documento soporte (Res. DIAN 167/2021): junta las compras de libro.json por proveedor y semana ISO y calcula el plazo.

Fuentes de los valores (docs/sdlc/03-design.md sección 6):
- Semana: lunes a domingo, ISO 8601 (R3).
- Plazo `misma_semana`: último día hábil de la semana en que ocurrió la compra (Res. 167/2021 art. 10 par.;
  DUR 1625/2016 art. 1.6.1.4.12; Res. 227/2025 sin verificar). `semana_siguiente`: el de la semana siguiente.
- Días hábiles: lunes a viernes menos los festivos de Colombia (Ley 51/1983) que el usuario lista en `festivos`.
- `aviso_dias`: días hábiles antes del límite en que la semana pasa a «vence_pronto» (interno).
"""
from __future__ import annotations
import sqlite3
from dataclasses import dataclass, field
from datetime import date, timedelta
from parser_module.contable import proveedores as prov

DEFECTO = {"regla_plazo": "misma_semana", "aviso_dias": 2, "festivos": []}
REGLAS = ("misma_semana", "semana_siguiente")
EN_PLAZO, VENCE_PRONTO, VENCIDA = "en_plazo", "vence_pronto", "vencida"


@dataclass(frozen=True)
class Compra:
    id: str
    fecha: str          # fecha de la compra, AAAA-MM-DD
    valor: int          # total pagado, en pesos
    tercero: str        # texto leído del papel
    origen: str         # papel de origen (N2)
    numero: str = ""


@dataclass
class Grupo:
    proveedor: prov.Proveedor | None   # None: el tercero no está registrado (R1/R2)
    tercero: str                       # nombre del papel, o el del proveedor si está registrado
    semana: str                        # «2026-W38»
    lunes: str
    domingo: str
    compras: list[Compra] = field(default_factory=list)
    total: int = 0
    fecha_limite: str = ""
    estado: str = EN_PLAZO
    dias_restantes: int = 0            # días hábiles que faltan hasta el límite (<0 si ya venció)


def config(c: dict | None) -> dict:
    """Mezcla contable.json con los defaults y valida la regla, los avisos y los festivos."""
    c = {**DEFECTO, **{k: v for k, v in (c or {}).items() if k in DEFECTO}}
    if c["regla_plazo"] not in REGLAS: raise ValueError(f"regla_plazo debe ser una de {REGLAS}, no {c['regla_plazo']!r}")
    if not isinstance(c["aviso_dias"], int) or c["aviso_dias"] < 0: raise ValueError("aviso_dias debe ser un entero >= 0")
    c["festivos"] = {date.fromisoformat(f) for f in c["festivos"]}
    return c


def es_habil(d: date, festivos) -> bool:
    return d.weekday() < 5 and d not in festivos


def ultimo_habil(lunes: date, festivos) -> date:
    """Último día hábil de la semana que empieza en `lunes` (si toda la semana es festiva, retrocede a la anterior)."""
    d = lunes + timedelta(days=6)
    while not es_habil(d, festivos): d -= timedelta(days=1)
    return d


def fecha_limite(fecha: date, regla: str, festivos) -> date:
    lunes = fecha - timedelta(days=fecha.weekday())
    if regla == "semana_siguiente": lunes += timedelta(days=7)
    return ultimo_habil(lunes, festivos)


def habiles_entre(hoy: date, limite: date, festivos) -> int:
    """Días hábiles que faltan después de `hoy` hasta `limite` incluido; negativo si el límite ya pasó."""
    if limite < hoy: return -sum(es_habil(limite + timedelta(days=i), festivos) for i in range(1, (hoy - limite).days + 1))
    return sum(es_habil(hoy + timedelta(days=i), festivos) for i in range(1, (limite - hoy).days + 1))


def estado(hoy: date, limite: date, aviso_dias: int, festivos) -> tuple[str, int]:
    n = habiles_entre(hoy, limite, festivos)
    if hoy > limite: return VENCIDA, min(n, -1)
    return (VENCE_PRONTO if n <= aviso_dias else EN_PLAZO), n


def compras_del_libro(libro: dict) -> list[Compra]:
    """Las facturas de compra con fecha y valor. Las duplicadas, las que no cuentan y las de valor 0 se saltan."""
    out = []
    for dia in libro.values():
        for d in dia.get("documentos", []):
            if d.get("tipo") != "factura" or not d.get("contar", True) or d.get("dup_de"): continue
            try: fecha = date.fromisoformat(d.get("fecha") or dia.get("fecha") or "")
            except ValueError: continue
            valor = int(d.get("valor") or 0)
            if valor > 0:
                out.append(Compra(d["id"], fecha.isoformat(), valor, (d.get("tercero") or "").strip(), d.get("origen", ""), d.get("numero", "")))
    return out


def semanas(libro: dict, con: sqlite3.Connection | None = None, cfg: dict | None = None, hoy: date | None = None,
            desde: str = "", hasta: str = "") -> list[Grupo]:
    """Grupos proveedor-semana de las compras entre `desde` y `hasta` (AAAA-MM-DD, opcionales); lo más urgente primero."""
    c = config(cfg)
    hoy = hoy or date.today()
    grupos: dict[tuple, Grupo] = {}
    for co in compras_del_libro(libro):
        if (desde and co.fecha < desde) or (hasta and co.fecha > hasta): continue
        f = date.fromisoformat(co.fecha)
        p = prov.resolver(con, co.tercero) if con is not None and co.tercero and not prov.es_encabezado(co.tercero) else None
        iso = f.isocalendar(); semana = f"{iso[0]}-W{iso[1]:02d}"
        llave = (("p", p.id) if p else ("t", prov.normalizar(co.tercero)), semana)
        g = grupos.get(llave)
        if g is None:
            lunes = f - timedelta(days=f.weekday())
            lim = fecha_limite(f, c["regla_plazo"], c["festivos"])
            est, n = estado(hoy, lim, c["aviso_dias"], c["festivos"])
            g = grupos[llave] = Grupo(p, p.nombre if p else co.tercero, semana, lunes.isoformat(),
                                      (lunes + timedelta(days=6)).isoformat(), fecha_limite=lim.isoformat(), estado=est, dias_restantes=n)
        g.compras.append(co); g.total += co.valor
    orden = {VENCIDA: 0, VENCE_PRONTO: 1, EN_PLAZO: 2}
    return sorted(grupos.values(), key=lambda g: (orden[g.estado], g.fecha_limite, g.tercero))
