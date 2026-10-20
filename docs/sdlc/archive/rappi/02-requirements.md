# 02 · Requisitos — Rappi (01c #6)  · tamaño S

## Summary
- **Problema:** los papeles de Rappi (≈ 19 en sept., p. ej. 17-09, ID 1000000003, «Total sugerido a facturar» $30.000) entran como venta sin número ni valor; 13452501 queda en 0 (manual [01f]).
- **Arreglo (R1):** reconocer el papel de Rappi por su formato y leer **ID de Rappi** (número del documento, sin comanda) y **«Total sugerido a facturar»** (valor); la venta entra con medio «Rappi» → débito 13452501 / crédito ingresos, tercero Rappi, medio App (ruta que ya existe en `asientos.py`).
- **Arreglo (R2):** un mismo ID de Rappi escaneado dos veces cuenta una sola venta (con aviso). **R3:** rige al recalcular sept., con respaldo del Excel anterior; el abono semanal del bloque «rappi» del extracto sigue saldando 13452501 sin cambios.
- **Prueba de aceptación:** dado el papel del 17-09, cuando se procesa, entonces hay una fila 13452501 débito $30.000 con número 1000000003 y medio App; y al recalcular sept. los papeles de Rappi suman en 13452501 cerca del manual ([01f]; la diferencia se explica papel por papel). Los papeles que no son de Rappi no cambian (pruebas de regresión en verde).
- **Fuera de alcance / riesgo:** fuera: leer el extracto bancario (#5), la comisión de Rappi como gasto, Didi/iFood. Riesgo: el OCR lee mal el total o el ID → la fila queda con aviso para revisar en ④, nunca con valor inventado.

## Open questions
- (ninguna; las 3 de triage ya están contestadas)
