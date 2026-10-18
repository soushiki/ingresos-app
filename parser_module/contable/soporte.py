"""Documento soporte (Res. DIAN 167/2021): junta las compras de libro.json por proveedor y semana ISO y calcula el plazo.

Fuentes de los valores (docs/sdlc/archive/documento-soporte/03-design.md sección 6):
- Semana: lunes a domingo, ISO 8601 (R3).
- Plazo `misma_semana`: último día hábil de la semana en que ocurrió la compra (Res. 167/2021 art. 10 par.;
  DUR 1625/2016 art. 1.6.1.4.12; Res. 227/2025 sin verificar). `semana_siguiente`: el de la semana siguiente.
- Días hábiles: lunes a viernes menos los festivos de Colombia (Ley 51/1983) que el usuario lista en `festivos`.
- `aviso_dias`: días hábiles antes del límite en que la semana pasa a «vence_pronto» (interno).
- `tolerancia_fecha_dias`: si la fecha leída del papel está a más de estos días del día del libro, el OCR la leyó mal
  (año o mes cambiado): la compra usa la fecha del día y el grupo avisa con las dos (interno, decisión del usuario FIX-9).
- Numeración (`generar`): consecutivo del rango DS autorizado, sin repetir ni reutilizar (Res. 167/2021 art. 4 y 5; ADR-003).
- Ciclo de vida (R7): generado → transmitido (con el CUDS que da la solución gratuita DIAN: SHA-384, 96 hexadecimales,
  Res. 167/2021 art. 4 y Anexo técnico) o generado → anulado (con motivo; el número queda gastado, ADR-003). Lo transmitido
  no cambia: `bloqueos` impide editar sus compras en el libro y se corrige con nota de ajuste (R8).
- Nota de ajuste (`nota_ajuste`, R8): consecutivo interno propio, clase NA, rango `rango_na` de contable.json (Res. 167/2021
  art. 5 y Res. 165/2023: nota de ajuste al documento soporte con referencia al documento que ajusta; prefijo y rango
  por confirmar con contabilidad, por defecto NA 1–10000).
"""
from __future__ import annotations
import json, re, sqlite3
from datetime import datetime, timezone
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from parser_module.contable import proveedores as prov, soporte_db as sdb

DEFECTO = {"regla_plazo": "misma_semana", "aviso_dias": 2, "tolerancia_fecha_dias": 7, "festivos": [],
           "rango_na": {"prefijo": "NA", "desde": 1, "hasta": 10000}}
PREFIJO = re.compile(r"[A-Z0-9]{1,4}")   # Anexo técnico DS: prefijo de hasta 4 caracteres alfanuméricos
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
    r = c["rango_na"]
    ent = lambda v: isinstance(v, int) and not isinstance(v, bool)
    if (not isinstance(r, dict) or not isinstance(r.get("prefijo"), str) or not PREFIJO.fullmatch(r["prefijo"])
            or not ent(r.get("desde")) or not ent(r.get("hasta")) or not 1 <= r["desde"] <= r["hasta"]):
        raise ValueError("rango_na debe ser {prefijo: hasta 4 letras o dígitos en mayúscula, desde: entero >= 1, hasta: entero >= desde}")
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
    motivo: str = ""                   # por qué se anuló
    cuds: str = ""                     # código único que dio la DIAN al transmitirlo (opcional)
    clase: str = "DS"                  # DS documento soporte · NA nota de ajuste (R8)
    ajusta_a: str = ""                 # NA: número del documento que ajusta («CTG-58»)
    concepto: str = ""                 # NA: por qué se ajusta


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
            did = con.execute("INSERT INTO documento(clase, prefijo, numero, proveedor_id, proveedor_json, semana_iso, fecha_generacion, total, iva, creado) "
                              "VALUES ('DS', ?, ?, ?, ?, ?, ?, ?, 0, ?)",
                              (prefijo, numero, g.proveedor.id, json.dumps(asdict(g.proveedor), ensure_ascii=False), g.semana, hoy.isoformat(),
                               total, creado)).lastrowid
            con.executemany("INSERT INTO linea(documento_id, fecha_compra, origen_fecha, origen_doc_id, descripcion, valor) VALUES (?, ?, ?, ?, ?, ?)",
                            [(did, l.fecha_compra, l.origen_fecha, l.origen_doc_id, l.descripcion, l.valor) for l in lineas])
            docs.append(Documento(did, prefijo, numero, g.proveedor, g.semana, hoy.isoformat(), total, lineas, g.fecha_limite))
    return docs


def _proveedor_fijo(con: sqlite3.Connection, r: sqlite3.Row) -> prov.Proveedor:
    """Los datos del vendedor tal como estaban al generar (art. 4 Res. 167/2021); sin copia, los de hoy."""
    if r["proveedor_json"]:
        d = json.loads(r["proveedor_json"])
        return prov.Proveedor(**{**d, "no_obligado": bool(d.get("no_obligado", True))})
    return prov.obtener(con, r["proveedor_id"])


def documentos(con: sqlite3.Connection, cfg: dict | None = None, ids: list[int] | None = None) -> list[Documento]:
    """Documentos DS y notas de ajuste NA, anulados incluidos (N1: su número sale en el RESUMEN).
    `fecha_limite` del DS se recalcula con `cfg`; la nota de ajuste no tiene plazo semanal."""
    c = config(cfg)
    out = []
    for r in con.execute("SELECT d.*, o.prefijo || '-' || o.numero AS ajusta_num FROM documento d LEFT JOIN documento o ON o.id = d.ajusta_a ORDER BY d.id"):
        if ids is not None and r["id"] not in ids: continue
        ls = [Linea(l["fecha_compra"], l["origen_fecha"], l["origen_doc_id"], l["descripcion"], l["valor"])
              for l in con.execute("SELECT * FROM linea WHERE documento_id = ? ORDER BY fecha_compra, origen_doc_id", (r["id"],))]
        y, w = r["semana_iso"].split("-W")
        lim = fecha_limite(date.fromisocalendar(int(y), int(w), 1), c["regla_plazo"], c["festivos"]).isoformat() if r["clase"] == "DS" else ""
        out.append(Documento(r["id"], r["prefijo"], r["numero"], _proveedor_fijo(con, r), r["semana_iso"], r["fecha_generacion"], r["total"], ls,
                             lim, r["estado"], r["iva"], r["motivo"] or "", r["cuds"] or "", r["clase"], r["ajusta_num"] or "", r["concepto"] or ""))
    return out


class NoSePuede(Exception):
    """Cambio de estado no permitido (R7, ADR-003)."""


CUDS = re.compile(r"[0-9a-f]{96}")


def _estado_de(con: sqlite3.Connection, doc_id: int) -> sqlite3.Row:
    r = con.execute("SELECT id, prefijo, numero, estado FROM documento WHERE id = ?", (doc_id,)).fetchone()
    if r is None: raise NoSePuede(f"no existe el documento {doc_id}")
    return r


def marcar_transmitido(con: sqlite3.Connection, doc_id: int, cuds: str | None = None) -> None:
    """generado → transmitido (R7). `cuds`: el que muestra la solución gratuita DIAN, SHA-384 en hexadecimal (96 caracteres)."""
    cuds = (cuds or "").strip().lower()
    if cuds and not CUDS.fullmatch(cuds): raise NoSePuede("El CUDS son 96 caracteres hexadecimales (0-9, a-f); déjelo vacío si no lo tiene")
    with sdb.transaccion(con):
        r = _estado_de(con, doc_id)
        if r["estado"] != "generado": raise NoSePuede(f"R7: {r['prefijo']}-{r['numero']} está {r['estado']}; solo un documento generado se marca transmitido")
        con.execute("UPDATE documento SET estado = 'transmitido', cuds = ? WHERE id = ? AND estado = 'generado'", (cuds or None, doc_id))


def anular(con: sqlite3.Connection, doc_id: int, motivo: str) -> None:
    """generado → anulado con motivo (ADR-003): el número queda gastado y sale en el RESUMEN; las compras quedan libres
    para un documento nuevo con otro número. Lo transmitido no se anula: se corrige con nota de ajuste (R8)."""
    motivo = (motivo or "").strip()
    if not motivo: raise NoSePuede("Escriba el motivo de la anulación")
    if len(motivo) > 200: raise NoSePuede("Motivo demasiado largo (máx. 200)")
    with sdb.transaccion(con):
        r = _estado_de(con, doc_id)
        if r["estado"] == "transmitido": raise NoSePuede(f"ADR-003: transmitido no se anula ({r['prefijo']}-{r['numero']}); prepare una nota de ajuste")
        if r["estado"] != "generado": raise NoSePuede(f"{r['prefijo']}-{r['numero']} ya está anulado")
        con.execute("UPDATE documento SET estado = 'anulado', motivo = ? WHERE id = ? AND estado = 'generado'", (motivo, doc_id))


MAX_VALOR = 10 ** 10   # el mismo tope de la compra manual (T14)


def nota_ajuste(con: sqlite3.Connection, doc_id: int, lineas: list[dict], concepto: str, cfg: dict | None = None,
                hoy: date | None = None) -> Documento:
    """Nota de ajuste (R8) sobre un documento DS transmitido: número NA propio del rango `rango_na` (Res. 167/2021 art. 5;
    Res. 165/2023), referencia `ajusta_a` al documento y su valor. Lo transmitido no se toca (ADR-003).

    `lineas`: [{descripcion, valor}] con valor entero en pesos ≠ 0 (negativo baja, positivo sube). El total no puede dejar
    el documento con valor negativo contando las otras notas no anuladas. Numerar y crear van en una transacción (N1).
    """
    rna = config(cfg)["rango_na"]
    hoy = hoy or date.today()
    concepto = concepto.strip() if isinstance(concepto, str) else ""
    if not concepto: raise NoSePuede("Escriba el concepto del ajuste (por qué se corrige)")
    if len(concepto) > 200: raise NoSePuede("Concepto demasiado largo (máx. 200)")
    if not isinstance(lineas, list) or not 1 <= len(lineas) <= 50: raise NoSePuede("La nota lleva entre 1 y 50 líneas")
    ls = []
    for i, l in enumerate(lineas, 1):
        if not isinstance(l, dict): raise NoSePuede(f"línea {i}: formato inválido")
        desc, v = l.get("descripcion"), l.get("valor")
        desc = desc.strip() if isinstance(desc, str) else ""
        if not desc or len(desc) > 200: raise NoSePuede(f"línea {i}: la descripción va de 1 a 200 caracteres")
        if not isinstance(v, int) or isinstance(v, bool) or v == 0 or abs(v) > MAX_VALOR:
            raise NoSePuede(f"línea {i}: el valor es un entero en pesos distinto de 0 (máx. {_pesos(MAX_VALOR)})")
        ls.append((desc, v))
    total = sum(v for _, v in ls)
    if total == 0: raise NoSePuede("El ajuste suma 0: no hay nada que corregir")
    creado = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with sdb.transaccion(con):
        o = con.execute("SELECT * FROM documento WHERE id = ?", (doc_id,)).fetchone()
        if o is None: raise NoSePuede(f"no existe el documento {doc_id}")
        num = f"{o['prefijo']}-{o['numero']}"
        if o["clase"] != "DS": raise NoSePuede(f"R8: {num} es una nota de ajuste; el ajuste se hace sobre el documento soporte")
        if o["estado"] != "transmitido":
            raise NoSePuede(f"R8: {num} está {o['estado']}; solo un documento transmitido lleva nota de ajuste"
                            + (" (un generado se anula y se vuelve a generar)" if o["estado"] == "generado" else ""))
        previo = con.execute("SELECT COALESCE(SUM(total), 0) FROM documento WHERE ajusta_a = ? AND estado != 'anulado'", (doc_id,)).fetchone()[0]
        if o["total"] + previo + total < 0:
            raise NoSePuede(f"R8: {num} vale {_pesos(o['total'] + previo)} con sus ajustes; un ajuste de {_pesos(total)} lo deja negativo")
        try: sdb.asegurar_rango(con, "NA", rna["prefijo"], rna["desde"], rna["hasta"])
        except ValueError as e: raise NoSePuede(str(e))
        prefijo, numero = sdb.reservar_numero(con, "NA")
        nid = con.execute("INSERT INTO documento(clase, prefijo, numero, proveedor_id, proveedor_json, semana_iso, fecha_generacion, total, iva, "
                          "ajusta_a, concepto, creado) VALUES ('NA', ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)",
                          (prefijo, numero, o["proveedor_id"], o["proveedor_json"], o["semana_iso"], hoy.isoformat(), total, doc_id, concepto, creado)).lastrowid
        # La línea apunta al documento ajustado, no a un papel del libro: así `documento_de` y `bloqueos` no la toman por una compra.
        lineas_na = [Linea(hoy.isoformat(), "", num, d, v) for d, v in ls]
        con.executemany("INSERT INTO linea(documento_id, fecha_compra, origen_fecha, origen_doc_id, descripcion, valor) VALUES (?, ?, ?, ?, ?, ?)",
                        [(nid, l.fecha_compra, l.origen_fecha, l.origen_doc_id, l.descripcion, l.valor) for l in lineas_na])
        p = _proveedor_fijo(con, o)
    return Documento(nid, prefijo, numero, p, o["semana_iso"], hoy.isoformat(), total, lineas_na, clase="NA", ajusta_a=num, concepto=concepto)


def _pesos(v: int) -> str:
    return f"{v:,}".replace(",", ".")


def bloqueos(con: sqlite3.Connection, fecha: str, docs: list[dict]) -> list[str]:
    """Lo llama el guardado del libro (R7): qué cambios de `docs` (los papeles nuevos del día `fecha`) tocan una compra que está
    en un documento transmitido. Cambiar su valor o su tercero (a otro proveedor), quitarla o dejar de contarla está prohibido."""
    nuevos = {d.get("id"): d for d in docs if isinstance(d, dict)}
    out = []
    for l in con.execute("SELECT l.origen_doc_id, l.valor, d.prefijo, d.numero, d.proveedor_id FROM linea l JOIN documento d ON d.id = l.documento_id "
                         "WHERE l.origen_fecha = ? AND d.estado = 'transmitido' ORDER BY d.numero, l.id", (fecha,)):
        n, num = nuevos.get(l["origen_doc_id"]), f"{l['prefijo']}-{l['numero']}"
        if n is None or n.get("tipo") != "factura" or not n.get("contar", True) or n.get("dup_de"):
            out.append(f"{num} (transmitido): la compra {l['origen_doc_id']} de {_pesos(l['valor'])} ya no está en el día; prepare una nota de ajuste")
            continue
        if int(n.get("valor") or 0) != l["valor"]:
            out.append(f"{num} (transmitido): la compra {l['origen_doc_id']} vale {_pesos(l['valor'])}, no {_pesos(int(n.get('valor') or 0))}; prepare una nota de ajuste")
        p = prov.resolver(con, (n.get("tercero") or "").strip())
        if p is None or p.id != l["proveedor_id"]:
            out.append(f"{num} (transmitido): la compra {l['origen_doc_id']} no puede cambiar de proveedor a «{(n.get('tercero') or '')[:60]}»")
    return out
