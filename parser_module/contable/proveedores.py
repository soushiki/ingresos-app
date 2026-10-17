"""Registro de proveedores no obligados a facturar (R1) y alias del tercero que lee el OCR (R2).

Los datos del vendedor que pide el documento soporte (Res. DIAN 167/2021 art. 4: nombre o razón social
y número de identificación) se guardan una vez en soporte.db y se reutilizan; nada sale de `datos/` (N3).
La conexión la abre `soporte_db.abrir`; aquí solo se recibe.
"""
from __future__ import annotations
import re, sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from parser_module.numeros import norm
from parser_module.contable import soporte_db as sdb

# Tipos de documento de identificación de la DIAN (anexo técnico de factura/documento soporte, tabla 13.2.1).
TIPOS_ID = {"RC": "11 Registro civil", "TI": "12 Tarjeta de identidad", "CC": "13 Cédula de ciudadanía",
            "TE": "21 Tarjeta de extranjería", "CE": "22 Cédula de extranjería", "NIT": "31 NIT",
            "PA": "41 Pasaporte", "PEP": "47 Permiso especial de permanencia", "PPT": "48 Permiso por protección temporal"}
_SOLO_DIGITOS = {"RC", "TI", "CC", "NIT"}
_PESOS_DV = (3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71)   # DIAN, de derecha a izquierda

# Lo que el OCR lee en la casilla del tercero y no es un nombre (R2).
ENCABEZADOS = {"sin texto", "proveedor", "proveedores", "tercero", "cliente", "vendedor", "nombre", "nombres",
               "razon social", "senor", "senores", "senor es", "nit", "cc", "c c", "cedula", "documento",
               "consumidor final", "cuantias menores", "caja", "fecha", "total", "valor", "concepto",
               "descripcion", "detalle", "direccion", "telefono", "ciudad", "factura", "recibo", "n a", "na"}


class DatosIncompletos(ValueError):
    """El proveedor o el alias no se puede guardar; el mensaje dice qué falta o qué está mal."""


@dataclass(frozen=True)
class Proveedor:
    id: int
    tipo_id: str
    num_id: str
    nombre: str
    direccion: str
    municipio: str
    correo: str | None
    no_obligado: bool


def normalizar(texto: str) -> str:
    """Llave de alias: minúsculas, sin tildes ni puntos, solo letras y dígitos separados por un espacio."""
    t = norm(texto or "").replace(".", "")
    return " ".join(re.findall(r"[a-z0-9]+", t))


def es_encabezado(texto: str) -> bool:
    """True si el «tercero» leído es un rótulo del papel («Sin Texto», «Proveedor:», «NIT»…) o no tiene letras."""
    t = normalizar(texto)
    return not re.search(r"[a-z]", t) or t in ENCABEZADOS


def digito_verificacion(nit: str) -> int:
    """DV del NIT según el algoritmo de la DIAN (módulo 11 con pesos primos)."""
    s = sum(int(d) * p for d, p in zip(reversed(nit), _PESOS_DV)) % 11
    return s if s < 2 else 11 - s


def _validar(datos: dict) -> dict:
    """Limpia y valida en el servidor (no solo en el formulario). Devuelve los campos listos para guardar."""
    tipo = (datos.get("tipo_id") or "").strip().upper()
    num = re.sub(r"[\s.]", "", datos.get("num_id") or "")
    nombre = " ".join((datos.get("nombre") or "").split())
    direccion = " ".join((datos.get("direccion") or "").split())
    municipio = " ".join((datos.get("municipio") or "").split())
    correo = (datos.get("correo") or "").strip() or None
    faltan, malos = [], []
    if not tipo: faltan.append("tipo de ID")
    elif tipo not in TIPOS_ID: malos.append(f"tipo de ID «{tipo}» (use uno de: {', '.join(TIPOS_ID)})")
    if not num: faltan.append("número de ID")
    elif tipo == "NIT" and re.fullmatch(r"\d{6,10}-\d", num):
        num, dv = num.split("-")
        if int(dv) != digito_verificacion(num):
            malos.append(f"dígito de verificación del NIT (para {num} es {digito_verificacion(num)}, no {dv})")
    if num and tipo in _SOLO_DIGITOS and not re.fullmatch(r"\d{3,11}", num):
        malos.append(f"número de ID «{num}» (solo dígitos, de 3 a 11)")
    elif num and not re.fullmatch(r"[0-9A-Za-z]{3,20}", num):
        malos.append(f"número de ID «{num}» (letras y dígitos, de 3 a 20)")
    for campo, valor, maximo in (("nombre", nombre, 200), ("dirección", direccion, 200), ("municipio", municipio, 80)):
        if not valor: faltan.append(campo)
        elif len(valor) > maximo: malos.append(f"{campo} (máximo {maximo} caracteres)")
    if correo and (len(correo) > 120 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", correo)):
        malos.append(f"correo «{correo}»")
    if faltan or malos:
        partes = ([f"falta {', '.join(faltan)}"] if faltan else []) + ([f"revise {'; '.join(malos)}"] if malos else [])
        raise DatosIncompletos("Proveedor no guardado: " + ". ".join(partes) + ".")
    return dict(tipo_id=tipo, num_id=num.upper(), nombre=nombre, direccion=direccion, municipio=municipio, correo=correo)


def _fila(r: sqlite3.Row | None) -> Proveedor | None:
    if r is None: return None
    return Proveedor(r["id"], r["tipo_id"], r["num_id"], r["nombre"], r["direccion"], r["municipio"], r["correo"], bool(r["no_obligado"]))


def obtener(con: sqlite3.Connection, proveedor_id: int) -> Proveedor | None:
    return _fila(con.execute("SELECT * FROM proveedor WHERE id = ?", (proveedor_id,)).fetchone())


def guardar(con: sqlite3.Connection, datos: dict) -> Proveedor:
    """Crea o actualiza (por número de ID) un proveedor no obligado; su nombre queda como alias si está libre."""
    d = _validar(datos)
    ahora = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with sdb.transaccion(con):
        pid = con.execute(
            "INSERT INTO proveedor(tipo_id, num_id, nombre, direccion, municipio, correo, no_obligado, creado) "
            "VALUES (:tipo_id, :num_id, :nombre, :direccion, :municipio, :correo, 1, :creado) "
            "ON CONFLICT(num_id) DO UPDATE SET tipo_id = excluded.tipo_id, nombre = excluded.nombre, "
            "direccion = excluded.direccion, municipio = excluded.municipio, correo = excluded.correo "
            "RETURNING id", {**d, "creado": ahora}).fetchone()[0]
        clave = normalizar(d["nombre"])
        if not es_encabezado(d["nombre"]):   # dos proveedores con el mismo nombre: el alias se queda con el primero
            con.execute("INSERT OR IGNORE INTO alias(texto_norm, proveedor_id) VALUES (?, ?)", (clave, pid))
    return obtener(con, pid)


def asociar(con: sqlite3.Connection, texto_ocr: str, proveedor_id: int, reasignar: bool = False) -> None:
    """Asocia el tercero leído por el OCR a un proveedor (R2). Un encabezado nunca se acepta como alias."""
    if es_encabezado(texto_ocr):
        raise DatosIncompletos(f"«{texto_ocr}» es un encabezado del papel, no un proveedor: elija el proveedor.")
    clave = normalizar(texto_ocr)
    with sdb.transaccion(con):
        if not con.execute("SELECT 1 FROM proveedor WHERE id = ?", (proveedor_id,)).fetchone():
            raise DatosIncompletos(f"No existe el proveedor {proveedor_id}.")
        actual = con.execute("SELECT proveedor_id FROM alias WHERE texto_norm = ?", (clave,)).fetchone()
        if actual and actual[0] != proveedor_id and not reasignar:
            raise DatosIncompletos(f"«{texto_ocr}» ya es de otro proveedor ({actual[0]}); use reasignar para cambiarlo.")
        con.execute("INSERT INTO alias(texto_norm, proveedor_id) VALUES (?, ?) "
                    "ON CONFLICT(texto_norm) DO UPDATE SET proveedor_id = excluded.proveedor_id", (clave, proveedor_id))


def resolver(con: sqlite3.Connection, texto_ocr: str) -> Proveedor | None:
    """Proveedor del alias, o None si es un encabezado o un texto aún sin asociar (la app pide elegir)."""
    if es_encabezado(texto_ocr): return None
    return _fila(con.execute("SELECT p.* FROM alias a JOIN proveedor p ON p.id = a.proveedor_id WHERE a.texto_norm = ?",
                             (normalizar(texto_ocr),)).fetchone())
