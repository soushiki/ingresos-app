# ADR-002 · MOVIMIENTOS con fórmulas que leen la hoja DATOS OCR

Estado: **confirmado** por el spike T4 (2026-10-16): en los 30 días de libro.json, los 408 asientos hechos con fórmulas dan lo mismo que `construir()` (evaluador propio de referencias, SUMIFS, MIN). Falta abrir `spike/spike_2026-09-20.xlsx` en Excel y ver «¿Cuadra?» = SÍ (en este equipo no hay Excel).

## Contexto
R9: corregir a mano lo que el OCR leyó mal y que el libro se recalcule. Las macros (.xlsm) quedan bloqueadas por Office. Opciones: 1) valores fijos (como hoy, no se propaga); **2) fórmulas con openpyxl**; 3) VBA (descartado: bloqueado y difícil de auditar).

## Decisión (opción 2, con el ajuste del spike)
- DATOS OCR tiene **una fila por papel y medio de pago** (una venta mixta da 2–3 filas). Columnas: fecha, archivo, tipo, número, tercero, detalle, valor, medio, cuenta, estado, aviso, **propina, domicilio, bloque** (venta · caja · factura · extracto · rappi), id. Una venta sin ninguna cifra leída igual tiene su fila («pendiente»).
- `estado`: ok · no cuenta (duplicado, desmarcado, cierre) · en extracto · pendiente. Solo «ok» suma. El extracto bancario también es una fila.
- Asientos agregados: `SUMIFS` por fecha (`$A`) + estado + bloque + cuenta (+ tercero y medio en ventas electrónicas). Facturas: referencia directa. Tope de propina/domicilio al efectivo: `MIN(...)`. Las contrapartidas (41401501, 11050501 de caja) son fórmulas sobre las celdas del día, así el día siempre cuadra.
- Criterios siempre literales (`"Efectivo"`, `"(sin medio)"`), nunca una celda vacía. Si una venta tiene propina en efectivo pero valor en efectivo 0, igual lleva su fila de efectivo con valor 0.

## Consecuencias
+ Cada cifra muestra de qué papel sale (resuelve la observación 6 de 01b).
− El reparto de propina y domicilio entre medios (redondeo proporcional de `repartir`) va como valor: si corriges el valor de una venta, corrige también su propina.
− Qué filas tiene MOVIMIENTOS se decide al exportar: una corrección que crea un grupo nuevo (otra cuenta u otro medio) no agrega una fila; eso va como nota en AVISOS (T6).
− openpyxl no calcula: pandas ve fórmulas sin valor. Los SUMIFS usan columnas completas, así entran las filas agregadas a mano.

## Fitness test (`probar_datos_ocr.py`)
- No hay `vbaProject.bin`. Todo importe de MOVIMIENTOS empieza con `=` («ADR-002: importe sin fórmula»). Ninguna fila sin código («ADR-002/R10: fila sin código»).
- Al evaluar las fórmulas (lógica de `spike/spike_adr002.py`) cada día da lo mismo que `construir()`.
