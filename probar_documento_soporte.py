"""Prueba del documento soporte (Res. DIAN 167/2021): base soporte.db (ADR-001), numeración reservada (ADR-003)."""
import sqlite3, tempfile, threading
from pathlib import Path
from parser_module.contable import soporte_db as sdb
ok = True
def chk(c, m):
    global ok; ok &= bool(c); print(("✓ " if c else "✗ ") + m)

tmp = Path(tempfile.mkdtemp())
RUTA = tmp / "soporte.db"

# ── T7 · esquema, migraciones y semilla ─────────────────────────────────────
con = sdb.abrir(RUTA)
ver = con.execute("PRAGMA user_version").fetchone()[0]
chk(ver == len(sdb.MIGRACIONES), f"user_version = {ver} (migraciones aplicadas: {len(sdb.MIGRACIONES)})")
tablas = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
chk({"proveedor", "alias", "rango", "documento", "linea"} <= tablas, f"tablas de la sección 4 de 03: {sorted(tablas)}")
rg = [tuple(r) for r in con.execute("SELECT clase, prefijo, desde, hasta, ultimo, activo FROM rango")]
chk(rg == [("DS", "CTG", 1, 10000, 0, 1)], f"semilla: rango DS CTG 1–10000 activo, sin usar: {rg}")
con.close()
con = sdb.abrir(RUTA)   # abrir otra vez no repite migraciones ni semilla
chk(con.execute("SELECT count(*) FROM rango").fetchone()[0] == 1 and con.execute("PRAGMA user_version").fetchone()[0] == ver,
    "abrir dos veces no duplica la semilla ni cambia la versión")
chk(con.execute("PRAGMA foreign_keys").fetchone()[0] == 1, "las llaves foráneas están activas")

# ── reservar_numero ─────────────────────────────────────────────────────────
try: sdb.reservar_numero(con, "DS"); fuera = False
except RuntimeError: fuera = True
chk(fuera, "reservar_numero fuera de una transacción → error (debe ir en BEGIN IMMEDIATE)")
with sdb.transaccion(con):
    n1 = sdb.reservar_numero(con, "DS"); n2 = sdb.reservar_numero(con, "DS")
chk((n1, n2) == (("CTG", 1), ("CTG", 2)), f"números consecutivos: {n1}, {n2}")
try:
    with sdb.transaccion(con):
        sdb.reservar_numero(con, "DS"); raise ValueError("falla a mitad")
except ValueError: pass
chk(con.execute("SELECT ultimo FROM rango WHERE clase='DS'").fetchone()[0] == 2, "si la transacción falla, el contador vuelve atrás")

# ── ADR-001 · UNIQUE(prefijo, numero) ───────────────────────────────────────
pid = con.execute("INSERT INTO proveedor(tipo_id, num_id, nombre, creado) VALUES ('CC', '1234567', 'Doña Rosa', '2026-10-17T00:00:00Z')").lastrowid
def doc(numero, estado="generado"):
    return con.execute("INSERT INTO documento(clase, prefijo, numero, proveedor_id, semana_iso, fecha_generacion, total, estado, creado) "
                       "VALUES ('DS', 'CTG', ?, ?, '2026-W42', '2026-10-17', 50000, ?, '2026-10-17T00:00:00Z')", (numero, pid, estado)).lastrowid
d1 = doc(1)
try: doc(1); repetido = False
except sqlite3.IntegrityError: repetido = True
chk(repetido, "ADR-001: UNIQUE(prefijo,numero) ausente" if not repetido else "ADR-001: un número repetido → IntegrityError")
try: doc(3, "borrador"); raro = False
except sqlite3.IntegrityError: raro = True
chk(raro, "estado fuera de {generado, transmitido, anulado} → IntegrityError")
otros = [p for p in Path(".").rglob("*.py") if p.name != "soporte_db.py" and "venv" not in p.parts and p.name != Path(__file__).name
         and "sqlite3.connect" in p.read_text(encoding="utf8", errors="ignore")]
chk(not otros, "ADR-001: solo soporte_db.py abre soporte.db" + (f" (también: {otros})" if otros else ""))

# ── ADR-003 · un anulado no se reutiliza ────────────────────────────────────
con.execute("UPDATE documento SET estado='anulado', motivo='proveedor equivocado' WHERE id=?", (d1,))
with sdb.transaccion(con): n3 = sdb.reservar_numero(con, "DS")
chk(n3 == ("CTG", 3), "ADR-003: número reutilizado" if n3 != ("CTG", 3) else f"tras anular CTG-1 el siguiente es {n3[0]}-{n3[1]}: el anulado no vuelve")

# ── rango agotado → error claro ─────────────────────────────────────────────
con.execute("UPDATE rango SET ultimo = hasta WHERE clase='DS'")
try:
    with sdb.transaccion(con): sdb.reservar_numero(con, "DS")
    msg = ""
except sdb.RangoAgotado as e: msg = str(e)
chk("CTG" in msg and "10000" in msg and "rango nuevo" in msg, f"rango agotado → error claro: «{msg}»")
try:
    with sdb.transaccion(con): sdb.reservar_numero(con, "NA")
    msg = ""
except sdb.RangoAgotado as e: msg = str(e)
chk("NA" in msg and "no hay rango" in msg, f"clase sin rango (NA, por confirmar) → error claro: «{msg}»")
try: con.execute("INSERT INTO rango(clase, prefijo, desde, hasta, ultimo, activo) VALUES ('DS', 'CTG2', 1, 10, 0, 1)"); dos = True
except sqlite3.IntegrityError: dos = False
chk(not dos, "solo un rango activo por clase")
con.close()

# ── concurrencia: dos hilos con su propia conexión no repiten números ───────
R2 = tmp / "conc.db"; sdb.abrir(R2).close(); vistos, errores = [], []
def reservar(k):
    c = sdb.abrir(R2)
    try:
        for _ in range(k):
            with sdb.transaccion(c): vistos.append(sdb.reservar_numero(c, "DS")[1])
    except Exception as e: errores.append(e)
    finally: c.close()
hs = [threading.Thread(target=reservar, args=(40,)) for _ in range(3)]
for h in hs: h.start()
for h in hs: h.join()
chk(not errores and sorted(vistos) == list(range(1, 121)), f"3 hilos × 40 reservas → 1…120 sin repetidos ni huecos (errores: {errores[:1]})")

print("\n" + ("TODO OK" if ok else "HAY FALLOS"))
