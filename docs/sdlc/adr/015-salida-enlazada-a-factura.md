# ADR-015 · Una salida que ya es una factura pagada por banco se enlaza y no genera asiento

Estado: aceptado (2026-10-20, aprobado por el usuario)

## Contexto
`construir()` paso 4 ya acredita 11200501 por cada factura/gasto con medio ≠ Efectivo. Si el pago de esa factura
aparece en el extracto (PAGO PSE, TRANSF A …) y además genera su asiento, el gasto y la salida de banco quedan dobles.
R4 solo hablaba de ventas; este es el mismo riesgo del lado de los gastos.

## Opciones
1. No hacer nada: la línea va al puente 51959501 y el usuario la marca «ya está en factura»; mientras tanto, el libro queda doble.
2. **Sugerir el enlace:** si hay un único documento de banco con el mismo valor exacto y una fecha a ±3 días (`ventana_factura_dias`) → `destino: factura`, sin asiento propio, y en revisión hasta que se confirme.
3. Conciliación automática completa (valor ± tolerancia, varios a uno): es Won't en v1.

## Decisión
Opción 2. Con 0 candidatos la línea sigue el flujo normal. Con 2 o más candidatos, va a revisión **sin asiento** y el aviso «¿cuál factura?».
Una factura no se enlaza a dos líneas.

## Consecuencias
+ El libro no duplica gastos ni siquiera antes de revisar. − Un valor igual por coincidencia puede enlazar algo que no es (por eso siempre se confirma).

## Fitness test (`probar_extracto.py`)
- Una factura de banco por 120 000 + una línea de −120 000 dos días después dan una sola fila de crédito 11200501. Mensaje: «ADR-015: gasto pagado contado dos veces».
