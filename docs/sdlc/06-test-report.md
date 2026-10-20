# 06 · Informe de pruebas — ciclo Rappi (01c #6), T4 medir septiembre

Método: script de una vez (fuera del repo) sobre una COPIA de `datos/libro.json` (el original quedó intacto, mismo hash antes y después).
Cada papel de Rappi se re-leyó desde su texto guardado con `parse_rappi` (T1), fecha de la carpeta, y se reconstruyó el día con `construir` (T2).
## Papeles de Rappi (septiembre)
- Encontrados: 21 papeles = 18 ID distintos (el 26-sep tiene 3 papeles repetidos en 6 fotos; cuentan una vez, R2).
- Sin aviso: 15 · con aviso «se usó el subtotal» (no se leyó el total sugerido): 3 (7, 24 y 30 sep).
- Ninguno quedó sin ID ni sin valor.
| Día | Papeles | Valor 13452501 |
|---|---|---|
| 02 | 1 | 25.000 |
| 03 | 1 | 194.400 |
| 05 | 1 | 34.800 |
| 06 | 3 | 137.500 |
| 07 | 1 | 34.800 (subtotal) |
| 11 | 1 | 84.600 |
| 17 | 1 | 30.000 |
| 24 | 1 | 24.000 (subtotal) |
| 25 | 1 | 25.000 |
| 26 | 3 ID (6 fotos) | 163.200 |
| 28 | 1 | 24.000 |
| 29 | 2 | 90.000 |
| 30 | 1 | 32.400 (subtotal) |
## Suma 13452501 de septiembre vs manual
- Antes: 0 (los papeles entraban como venta sin número ni valor, o sin cuenta Rappi).
- Ahora: **[01f]**. Manual ≈ 2.400.000 → faltan ≈ 1.46 M (≈ 61 %).
- Explicación: el libro solo tiene papeles de Rappi en 13 de 30 días; 17 días no traen ninguno (8–10, 12–16, 18–23, 27, 1, 4).
  No hay papeles de Rappi sin detectar en el texto guardado (solo una nota de un vale y una referencia al nombre de la foto).
  La diferencia es de papeles no fotografiados o no cargados, no de lectura. Se cierra al cargar esos papeles (el bloque
  «rappi» del extracto ya salda 13452501 con los pagos semanales).
## Ventas que no son de Rappi
- Mismo código, papeles viejos vs re-leídos: en los 13 días con Rappi y en los 17 sin Rappi solo cambian las filas de abajo.
- Cambios por la lectura nueva, solo en días con Rappi: ingresos 41401501 sube lo que antes no se leía; el ajuste al cierre
  13809501 baja en 4 días (6, 7, 29, 30 sep) porque el papel de Rappi ya trae su valor (el total del cierre no cambia);
  11-sep: 28150502 baja [01f] (causa no investigada, a revisar). Débito = crédito en todos.
- El libro guardado difiere del código actual en 9 días por reglas posteriores a su guardado (no por Rappi): se arregla al recalcular (T3 ya respalda).
## Suites
Todas las `probar_*.py` verdes (probar_imagen.py es una herramienta con argumentos, no una suite).
