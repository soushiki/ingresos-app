# 06 · Informe de pruebas — vocabulario de medio de pago (01c #8), iteración 1 · 2.ª pasada

## Summary
- **PASA → 7-release.** 19/19 suites en verde tras FIX-1 (commit 415e7e7). R1–R4 cubiertos (sin cambios desde la 1.ª pasada).
- Cobertura (probar_medios.py): R1 (sinónimos → canónico; desconocido → vacío + aviso) · R2 (asientos sin caja → `medio=""`) ·
  R3 (venta mixta repartida; factura Mixto → mayor pago + aviso) · R4 (libro viejo → solo los 8 o vacío) · FIX-1 (recaudos con «· Ordenes:»).

## Failures
- Ninguna (`probar_*.py`, 19; `probar_imagen.py` es herramienta).

## Review findings (FIX-1, diff 85504b7..415e7e7)
- `asientos.py:368`: el paréntesis pega «· Ordenes: …» a cualquiera de los tres textos. Correcto y mínimo.
- Visto en salida: probar_contable «Recaudos con tarjetas · Ordenes: 8»; probar_medios: Nequi, transferencias, tarjetas y Rappi con órdenes.
- El check nuevo de probar_medios falla sin el fix (comprobado en 5-implement).
- Siguen las dos bajas de la 1.ª pasada, sin tarea: «Crédito» viejo → Tarjeta (no mueve cifras); prefijo `pse` en «pseudo…» (riesgo bajo).
- `/security-review`: no aplica (exposed no; sin auth, BD ni secretos).

## Debt check
- FIX-1: 1 línea de código + 3 de prueba. Sin DEBT nuevo.

## Smoke
- Cubierto por pruebas: 1 (11200501 con «· Ordenes:») y 4 (Rappi 13452501, medio App, «Ventas por Rappi · Ordenes:»).
- Para el usuario (≈5 min, con la app abierta):
  1. Recalcular 2026-09-16 → MOVIMIENTOS: filas 11200501 con «Recaudos … · Ordenes: …».
  2. DATOS OCR: «Medio de pago» solo con los 8 o vacío; «Medio según el papel» con Nequi/Datáfono donde corresponda.
  3. App ③ compra manual con «Nequi» → se guarda como Transferencia; el desplegable de ④ Revisión muestra los 8.
