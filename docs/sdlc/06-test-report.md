# 06 · Informe de pruebas — vocabulario de medio de pago (01c #8), iteración 1 · 1.ª pasada

## Summary
- **FALLA → FIX-1 (5-implement).** 19/19 suites en verde, pero la revisión del diff encontró una regresión en la descripción de los recaudos.
- Cobertura (probar_medios.py): R1 (cada sinónimo del mapa → canónico; desconocido → vacío + aviso) · R2 (2815, puentes, cierre,
  venta sin medio → `medio=""` con aviso) · R3 (venta mixta repartida sin «Mixto»; factura Mixto → mayor pago + aviso) · R4 (fixture libro viejo
  → Excel solo con los 8 o vacío; septiembre en memoria: 6 medios + vacío). Todas tienen prueba.

## Failures
- Ninguna en las suites (`probar_*.py`, 19; `probar_imagen.py` es herramienta).

## Review findings (diff 550907b..HEAD)
- **FIX-1 (alta, regresión):** `asientos.py:368`: `desc = A or B or f"…" + ords`. El `+ " · Ordenes: …"` solo se pega al último respaldo,
  así que las filas de banco/Rappi/crédito perdieron «· Ordenes: 85531» (v1.4.0 lo ponía siempre). Visto en la salida de probar_contable:
  «Recaudos con tarjetas» sin órdenes. Ninguna prueba lo cubre → agregar check.
- Baja, sin tarea: un `medio` «Crédito» guardado por la revisión vieja (REV_TEXTOS v1.4) se lee como Tarjeta (clave «credito»). En ventas
  `medio` no mueve asientos (se reparte por montos), así que no cambia cifras.
- Baja, sin tarea: el mapa busca por prefijo de palabra (`app`, `qr`, `pse`); un texto como «pseudo…» daría PSE. Solo se usa en las zonas de
  medio de pago, así que el riesgo es bajo.
- `/security-review`: no aplica (exposed no; sin auth, BD ni secretos; app.py solo cambia la validación del medio, que se endurece).

## Debt check
- +~60 líneas de código, un mapa nuevo y `medio_detalle` en una columna. Se borraron `MEDIOS_COMPRA` y la lista vieja `MEDIOS`. Sin DEBT nuevo.

## Smoke (pendiente, después de FIX-1)
1. Recalcular 2026-09-16 → MOVIMIENTOS: filas 11200501 con «Recaudos … · Ordenes: …».
2. DATOS OCR: «Medio de pago» solo con los 8 o vacío; «Medio según el papel» con Nequi/Datáfono donde corresponda.
3. App ③ compra manual con «Nequi» → se guarda como Transferencia; el desplegable de ④ Revisión muestra los 8.
4. Fila Rappi: 13452501, medio App, «Ventas por Rappi · Ordenes: <ID>».
