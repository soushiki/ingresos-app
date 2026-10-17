# ADR-001 · SQLite para los datos del documento soporte

Estado: aceptado (2026-10-16)

## Contexto
Hoy todo se guarda en JSON en `datos/`, con escritura tmp + replace y un `threading.Lock`. El documento soporte suma entidades relacionadas (proveedor, documento, línea, rango) y una regla dura: un número nunca se repite (N1).

## Opciones
1. JSON nuevo (`soporte.json`): sin dependencias, pero la unicidad del número y la regla «una compra en un solo documento» quedan solo en código, y un corte a mitad de una escritura puede dejar el contador atrás.
2. **SQLite (`sqlite3` de la stdlib) solo para lo nuevo**: tiene UNIQUE, transacciones `BEGIN IMMEDIATE` y journal; no hay que instalar nada.
3. Migrar todo el libro a SQLite: más correcto a largo plazo, pero mueve código que hoy funciona y no lo exige ningún requisito.

## Decisión
Opción 2. `libro.json` sigue siendo la fuente de las compras. `soporte.db` guarda proveedores, alias, rangos, documentos y líneas. Solo `contable/soporte_db.py` abre la base. El esquema se versiona con `PRAGMA user_version`.

## Consecuencias
+ La base garantiza N1 aunque haya un error en el código.
− Hay dos almacenes: el vínculo es `linea.origen_fecha + origen_doc_id`, y `bloqueos()` vigila que coincidan.
− Para respaldar `datos/` hay que copiar también el `.db` (anotarlo en 07-release).

## Fitness test (`probar_documento_soporte.py`)
- Insertar dos documentos con el mismo (prefijo, numero) debe fallar. Mensaje si no falla: «ADR-001: UNIQUE(prefijo,numero) ausente».
- Ningún archivo fuera de `soporte_db.py` contiene `sqlite3.connect`. Mensaje: «ADR-001: solo soporte_db.py abre soporte.db».
