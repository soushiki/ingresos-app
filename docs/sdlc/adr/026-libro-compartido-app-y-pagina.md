# ADR-026 · Un solo `libro.py` para la app y la página del contador

Estado: aceptado (2026-10-26, aprobado por el usuario en 3-design del modo contador web)

## Contexto
El spike (01) probó que `leer_crudo` → `construir` → `libro_a_excel` corre igual en Pyodide. Pero el Excel con extracto depende del pegamento que hoy vive en `app.py`: repartir las líneas por día y crear los días que faltan (`cont_extracto`), las facturas cercanas/usadas (`_facturas_cerca`, `_facturas_usadas`, ADR-015) y el recálculo final (`cont_excel`). Copiarlo a la página = dos cálculos que se separan con el tiempo (lo que ADR-002 prohíbe), y R2 exige el mismo Excel que la app.

## Opciones
1. Copiar el pegamento a un archivo de la página. Rápido, pero diverge en silencio.
2. **Mover ese pegamento a `parser_module/contable/libro.py` (funciones puras, sin Flask, sin disco) y que `app.py` lo llame.**
3. Que la página levante la app Flask entera en Pyodide. Arrastra Flask, sqlite, OCR: pesado y fuera de la lista blanca.

## Decisión
Opción 2. `libro.py` expone `desde_crudo`, `aplicar_extracto`, `excel` y `generar` (firmas en 03 §5). `app.py` mantiene las rutas, el LOCK, la lectura/escritura de archivos y las respuestas JSON; el cálculo sale de `libro.py`. El refactor no cambia ninguna salida: la suite actual (`probar_*.py`) tiene que seguir verde sin tocar sus expectativas.

## Consecuencias
+ Un solo cálculo: lo que se arregle en la app llega a la página en el siguiente tag.
+ `libro.generar` se prueba en CPython (rápido) y en Pyodide (contrato) con la misma entrada.
− Toca `app.py` en un ciclo `regulated: yes`: la task del refactor va primero y sola, con la suite completa antes y después.

## Fitness test (`probar_web.py`)
- `app.py` ya no define `_facturas_cerca` ni `_facturas_usadas`, y `cont_extracto`/`cont_excel` llaman a `libro.` → si no: «ADR-026: el pegamento del libro volvió a app.py».
- `libro.py` no importa `flask`, `sqlite3`, `ocr_module` ni `app` → «ADR-026: libro.py debe correr en el navegador».
- Mismo crudo + extracto + `ahora`: `libro.generar` = camino HTTP de la app (`/api/contable/extracto` + `/api/contable/excel`), 0 celdas distintas.
