"""Base `soporte.db` del documento soporte (ADR-001): el único módulo que la abre.

Dinero en pesos enteros, fechas ISO, hora UTC. El esquema se versiona con `PRAGMA user_version`;
cada migración nueva se agrega al final de MIGRACIONES y nunca se edita una ya publicada.
"""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

MIGRACIONES = [
    """
    CREATE TABLE proveedor(
        id INTEGER PRIMARY KEY, tipo_id TEXT NOT NULL, num_id TEXT NOT NULL UNIQUE, nombre TEXT NOT NULL,
        direccion TEXT, municipio TEXT, correo TEXT, no_obligado INTEGER NOT NULL DEFAULT 1, creado TEXT NOT NULL);
    CREATE TABLE alias(texto_norm TEXT PRIMARY KEY, proveedor_id INTEGER NOT NULL REFERENCES proveedor(id));
    -- Rango de numeración: DS lo autoriza la DIAN al negocio; NA es consecutivo interno propio (Res. 167/2021 art. 5).
    CREATE TABLE rango(
        id INTEGER PRIMARY KEY, clase TEXT NOT NULL CHECK (clase IN ('DS', 'NA')), prefijo TEXT NOT NULL,
        desde INTEGER NOT NULL, hasta INTEGER NOT NULL, ultimo INTEGER NOT NULL, activo INTEGER NOT NULL DEFAULT 1,
        CHECK (desde <= hasta AND ultimo BETWEEN desde - 1 AND hasta));
    CREATE UNIQUE INDEX rango_activo ON rango(clase) WHERE activo = 1;
    -- Campos del art. 4 de la Res. 167/2021; firma, formato y CUDS los pone la solución gratuita DIAN.
    CREATE TABLE documento(
        id INTEGER PRIMARY KEY, clase TEXT NOT NULL CHECK (clase IN ('DS', 'NA')), prefijo TEXT NOT NULL, numero INTEGER NOT NULL,
        proveedor_id INTEGER NOT NULL REFERENCES proveedor(id), semana_iso TEXT NOT NULL, fecha_generacion TEXT NOT NULL,
        total INTEGER NOT NULL, iva INTEGER NOT NULL DEFAULT 0,
        estado TEXT NOT NULL DEFAULT 'generado' CHECK (estado IN ('generado', 'transmitido', 'anulado')),
        motivo TEXT, cuds TEXT, ajusta_a INTEGER REFERENCES documento(id), creado TEXT NOT NULL,
        UNIQUE (prefijo, numero));
    -- Copia fija del valor con referencia al papel de libro.json (N2).
    CREATE TABLE linea(
        id INTEGER PRIMARY KEY, documento_id INTEGER NOT NULL REFERENCES documento(id), fecha_compra TEXT NOT NULL,
        origen_fecha TEXT NOT NULL, origen_doc_id TEXT NOT NULL, descripcion TEXT NOT NULL, valor INTEGER NOT NULL);
    CREATE INDEX linea_origen ON linea(origen_fecha, origen_doc_id);
    -- Autorización de numeración DIAN del negocio: prefijo CTG, 1–10000.
    INSERT INTO rango(clase, prefijo, desde, hasta, ultimo, activo) VALUES ('DS', 'CTG', 1, 10000, 0, 1);
    """,
    # T15: copia de los datos del vendedor del día de generación (art. 4 Res. 167/2021); editar el proveedor después
    # no cambia un documento ya numerado. Los documentos que ya existían se llenan con los datos de hoy (lo único que hay).
    """
    ALTER TABLE documento ADD COLUMN proveedor_json TEXT;
    UPDATE documento SET proveedor_json = (SELECT json_object('id', p.id, 'tipo_id', p.tipo_id, 'num_id', p.num_id, 'nombre', p.nombre,
        'direccion', p.direccion, 'municipio', p.municipio, 'correo', p.correo, 'no_obligado', p.no_obligado = 1)
        FROM proveedor p WHERE p.id = documento.proveedor_id);
    """,
]


class RangoAgotado(Exception):
    """No hay número disponible: el rango llegó a `hasta` o la clase no tiene rango activo."""


def abrir(ruta) -> sqlite3.Connection:
    """Abre (o crea) la base y aplica las migraciones pendientes. Autocommit: las escrituras van en `transaccion`."""
    Path(ruta).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(ruta, timeout=10, isolation_level=None, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    migrar(con)
    return con


def migrar(con: sqlite3.Connection) -> None:
    with transaccion(con):   # BEGIN IMMEDIATE: dos procesos abriendo a la vez no migran dos veces
        ver = con.execute("PRAGMA user_version").fetchone()[0]
        for i, sql in enumerate(MIGRACIONES[ver:], ver + 1):
            sql = "\n".join(l for l in sql.splitlines() if not l.lstrip().startswith("--"))   # un «;» en un comentario no corta
            for stmt in (s for s in sql.split(";") if s.strip()):
                con.execute(stmt)
            con.execute(f"PRAGMA user_version = {i}")


@contextmanager
def transaccion(con: sqlite3.Connection):
    """BEGIN IMMEDIATE … COMMIT; si algo falla, ROLLBACK (el contador del rango vuelve atrás)."""
    con.execute("BEGIN IMMEDIATE")
    try:
        yield con
    except BaseException:
        con.execute("ROLLBACK"); raise
    con.execute("COMMIT")


def reservar_numero(con: sqlite3.Connection, clase: str) -> tuple[str, int]:
    """Gasta el siguiente número del rango activo de `clase` ('DS' o 'NA') y devuelve (prefijo, número).

    Va dentro de la misma transacción que crea el documento (ADR-003): el número nunca se libera,
    ni al anular (Res. DIAN 167/2021 art. 4 y 5: consecutivo sin repetir).
    """
    if not con.in_transaction:
        raise RuntimeError("reservar_numero va dentro de soporte_db.transaccion (BEGIN IMMEDIATE)")
    r = con.execute("UPDATE rango SET ultimo = ultimo + 1 WHERE clase = ? AND activo = 1 AND ultimo < hasta "
                    "RETURNING prefijo, ultimo", (clase,)).fetchone()
    if r: return r["prefijo"], r["ultimo"]
    rg = con.execute("SELECT prefijo, desde, hasta FROM rango WHERE clase = ? AND activo = 1", (clase,)).fetchone()
    if not rg:
        raise RangoAgotado(f"{clase}: no hay rango de numeración activo; regístrelo antes de generar.")
    raise RangoAgotado(f"{clase}: el rango {rg['prefijo']} {rg['desde']}–{rg['hasta']} está agotado; "
                       f"pida a la DIAN un rango nuevo y regístrelo antes de generar.")
