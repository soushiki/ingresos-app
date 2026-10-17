"""Documento soporte (Res. DIAN 167/2021): junta las compras de libro.json por proveedor y semana ISO y calcula el plazo.

Fuentes de los valores (docs/sdlc/03-design.md sección 6):
- Semana: lunes a domingo, ISO 8601 (R3).
- Plazo `misma_semana`: último día hábil de la semana en que ocurrió la compra (Res. 167/2021 art. 10 par.;
  DUR 1625/2016 art. 1.6.1.4.12; Res. 227/2025 sin verificar). `semana_siguiente`: el de la semana siguiente.
- Días hábiles: lunes a viernes menos los festivos de Colombia (Ley 51/1983) que el usuario lista en `festivos`.
- `aviso_dias`: días hábiles antes del límite en que la semana pasa a «vence_pronto» (interno).
- `tolerancia_fecha_dias`: si la fecha leída del papel está a más de estos días del día del libro, el OCR la leyó mal
  (año o mes cambiado): la compra usa la fecha del día y el grupo avisa con las dos (interno, decisión del usuario FIX-9).
- Numeración (`generar`): consecutivo del rango DS autorizado, sin repetir ni reutilizar (Res. 167/2021 art. 4 y 5; ADR-003).
"""
from __future__ import annotations
import sqlite3
from datetime import datetime, timezone
from dataclasses import dataclass, field
from datetime import date, timedelta
from parser_module.contable import proveedores as prov, soporte_db as sdb

DEFECTO = {"regla_plazo": "misma_semana", "aviso_dias": 2, "tolerancia_fecha_dias": 7, "festivos": []}
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
    dia: str = ""        # llave del día en libro.json (origen_fecha de la línea, N2)
    descripcion: str = ""
    fecha_papel: str = ""  # la fecha leída del papel cuando se descartó por dudosa (FIX-9); "" si es la misma `fecha`


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
    documentado: str = ""              # «CTG-1» si estas compras ya están en ese documento no anulado (R3)
    elegir: bool = False               # el tercero leído es un rótulo («Sin Texto») o está vacío: una compra por grupo (R2)
    avisos: list[str] = field(default_factory=list)   # fechas del papel descartadas por dudosas (FIX-9)


def config(c: dict | None) -> dict:
    """Mezcla contable.json con los defaults y valida la regla, los avisos y los festivos."""
    c = {**DEFECTO, **{k: v for k, v in (c or {}).items() if k in DEFECTO}}
    if c["regla_plazo"] not in REGLAS: raise ValueError(f"regla_plazo debe ser una de {REGLAS}, no {c['regla_plazo']!r}")
    if not isinstance(c["aviso_dias"], int) or c["aviso_dias"] < 0: raise ValueError("aviso_dias debe ser un entero >= 0")
    t = c["tolerancia_fecha_dias"]
    if not isinstance(t, int) or isinstance(t, bool) or t < 0: raise ValueError("tolerancia_fecha_dias debe ser un entero >= 0")
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


def _fecha(s) -> date | None:
    try: return date.fromisoformat(s or "")
    except (TypeError, ValueError): return None


def compras_del_libro(libro: dict, tolerancia_fecha_dias: int = DEFECTO["tolerancia_fecha_dias"]) -> list[Compra]:
    """Las facturas de compra con fecha y valor. Las duplicadas, las que no cuentan y las de valor 0 se saltan.

    Si la fecha del papel está a más de `tolerancia_fecha_dias` del día del libro, se usa la del día (FIX-9).
    """
    out = []
    for k, dia in libro.items():
        del_dia = _fecha(dia.get("fecha") or k)
        for d in dia.get("documentos", []):
            if d.get("tipo") != "factura" or not d.get("contar", True) or d.get("dup_de"): continue
            fecha, papel = _fecha(d.get("fecha")), ""
            if fecha and del_dia and abs((fecha - del_dia).days) > tolerancia_fecha_dias: fecha, papel = del_dia, d["fecha"]
            if fecha is None and d.get("fecha") and del_dia: papel = str(d["fecha"])   # ilegible: también se avisa
            fecha = fecha or del_dia
            if fecha is None: continue
            valor = int(d.get("valor") or 0)
            if valor > 0:
                out.append(Compra(d["id"], fecha.isoformat(), valor, (d.get("tercero") or "").strip(), d.get("origen", ""), d.get("numero", ""),
                                  dia.get("fecha") or k, (d.get("descripcion") or "").strip(), papel))
    return out


def documento_de(con: sqlite3.Connection, dia: str, doc_id: str) -> str:
    """Número («CTG-1») del documento no anulado que ya tiene la compra, o "" (R3)."""
    r = con.execute("SELECT d.prefijo, d.numero FROM linea l JOIN documento d ON d.id = l.documento_id "
                    "WHERE l.origen_fecha = ? AND l.origen_doc_id = ? AND d.estado != 'anulado'", (dia, doc_id)).fetchone()
    return f"{r['prefijo']}-{r['numero']}" if r else ""


def semanas(libro: dict, con: sqlite3.Connection | None = None, cfg: dict | None = None, hoy: date | None = None,
            desde: str = "", hasta: str = "") -> list[Grupo]:
    """Grupos proveedor-semana de las compras entre `desde` y `hasta` (AAAA-MM-DD, opcionales); lo más urgente primero.

    Con `con`, las compras ya documentadas van en un grupo por documento (`documentado`) y las demás de la misma
    semana forman su propio grupo, que se numera aparte (R3).
    """
    c = config(cfg)
    hoy = hoy or date.today()
    grupos: dict[tuple, Grupo] = {}
    for co in compras_del_libro(libro, c["tolerancia_fecha_dias"]):
        if (desde and co.fecha < desde) or (hasta and co.fecha > hasta): continue
        f = date.fromisoformat(co.fecha)
        elegir = prov.es_encabezado(co.tercero)   # «Sin Texto» no es un proveedor: no se suma con otros «Sin Texto» (R2)
        p = prov.resolver(con, co.tercero) if con is not None and not elegir else None
        iso = f.isocalendar(); semana = f"{iso[0]}-W{iso[1]:02d}"
        hecho = documento_de(con, co.dia, co.id) if con is not None else ""
        quien = ("p", p.id) if p else ("c", co.dia, co.id) if elegir else ("t", prov.normalizar(co.tercero))
        llave = (quien, semana, hecho)
        g = grupos.get(llave)
        if g is None:
            lunes = f - timedelta(days=f.weekday())
            lim = fecha_limite(f, c["regla_plazo"], c["festivos"])
            est, n = estado(hoy, lim, c["aviso_dias"], c["festivos"])
            g = grupos[llave] = Grupo(p, p.nombre if p else co.tercero, semana, lunes.isoformat(),
                                      (lunes + timedelta(days=6)).isoformat(), fecha_limite=lim.isoformat(), estado=est, dias_restantes=n,
                                      documentado=hecho, elegir=elegir)
        g.compras.append(co); g.total += co.valor
        if co.fecha_papel: g.avisos.append(f"{co.origen or co.id}: el papel dice {co.fecha_papel}; se usa la fecha del día {co.fecha}")
    orden = {VENCIDA: 0, VENCE_PRONTO: 1, EN_PLAZO: 2}
    return sorted(grupos.values(), key=lambda g: (orden[g.estado], g.fecha_limite, g.tercero))


@dataclass
class Linea:
    fecha_compra: str
    origen_fecha: str
    origen_doc_id: str
    descripcion: str
    valor: int


@dataclass
class Documento:
    id: int
    prefijo: str
    numero: int
    proveedor: prov.Proveedor
    semana: str
    fecha_generacion: str
    total: int
    lineas: list[Linea]
    fecha_limite: str = ""             # del grupo, para el RESUMEN; no se guarda
    estado: str = "generado"
    iva: int = 0


class NoSeGenera(Exception):
    """El lote no se numera: proveedor sin registrar, compra ya documentada o semana vencida sin confirmar."""


def _descripcion(co: Compra) -> str:
    return co.descripcion or (f"Factura {co.numero}" if co.numero else "Compra") + (f" ({co.origen})" if co.origen else "")


def generar(con: sqlite3.Connection, grupos: list[Grupo], confirmar_vencidos: bool = False, hoy: date | None = None) -> list[Documento]:
    """Numera un documento DS por grupo, todo en una transacción BEGIN IMMEDIATE (ADR-003, N1): o salen todos o ninguno.

    Rechaza el lote si un grupo no tiene proveedor registrado (R1), si una compra ya está en otro documento
    no anulado (R3, nada se documenta dos veces) o si hay semanas vencidas y `confirmar_vencidos` es False (R6).
    Cada `linea` guarda una copia fija del valor y la referencia al papel de libro.json (N2).
    """
    hoy = hoy or date.today()
    grupos = [g for g in grupos if g.compras]
    sin = [g.tercero or "(sin nombre)" for g in grupos if g.proveedor is None]
    if sin: raise NoSeGenera(f"R1: registre al proveedor antes de generar: {', '.join(sin)}")
    venc = [f"{g.tercero} {g.semana}" for g in grupos if g.estado == VENCIDA]
    if venc and not confirmar_vencidos:
        raise NoSeGenera(f"R6: semanas vencidas, confirme para numerarlas: {', '.join(venc)}")
    llaves = [(co.dia, co.id) for g in grupos for co in g.compras]
    if len(set(llaves)) != len(llaves): raise NoSeGenera("R3: una compra aparece en dos grupos del mismo lote")
    for co in (co for g in grupos for co in g.compras):
        if not isinstance(co.valor, int) or co.valor <= 0: raise NoSeGenera(f"compra {co.id}: el valor debe ser un entero > 0")
        if not co.dia or not co.id: raise NoSeGenera(f"compra {co.id!r}: falta la referencia al papel (N2)")
    creado = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    docs = []
    with sdb.transaccion(con):
        for dia, did in llaves:   # dentro del BEGIN IMMEDIATE: otro proceso no puede colarse entre la revisión y el INSERT
            hecho = documento_de(con, dia, did)
            if hecho: raise NoSeGenera(f"R3: la compra {did} del {dia} ya está en {hecho}")
        for g in grupos:
            prefijo, numero = sdb.reservar_numero(con, "DS")
            lineas = [Linea(co.fecha, co.dia, co.id, _descripcion(co), co.valor) for co in sorted(g.compras, key=lambda c: (c.fecha, c.id))]
            total = sum(l.valor for l in lineas)
            did = con.execute("INSERT INTO documento(clase, prefijo, numero, proveedor_id, semana_iso, fecha_generacion, total, iva, creado) "
                              "VALUES ('DS', ?, ?, ?, ?, ?, ?, 0, ?)",
                              (prefijo, numero, g.proveedor.id, g.semana, hoy.isoformat(), total, creado)).lastrowid
            con.executemany("INSERT INTO linea(documento_id, fecha_compra, origen_fecha, origen_doc_id, descripcion, valor) VALUES (?, ?, ?, ?, ?, ?)",
                            [(did, l.fecha_compra, l.origen_fecha, l.origen_doc_id, l.descripcion, l.valor) for l in lineas])
            docs.append(Documento(did, prefijo, numero, g.proveedor, g.semana, hoy.isoformat(), total, lineas, g.fecha_limite))
    return docs
