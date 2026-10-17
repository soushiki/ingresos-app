# ADR-003 · El número se reserva al generar y nunca se libera

Estado: aceptado (2026-10-16)

## Contexto
La DIAN autoriza el rango CTG 1–10000 y no permite reutilizar números (Res. 167/2021 art. 4 y 5). La app prepara el documento y alguien lo transcribe después a la solución gratuita, que asigna su propio CUDS.

## Opciones
1. Numerar al exportar el Excel: si se exporta dos veces, salen números distintos para el mismo documento.
2. **Numerar al generar, dentro de la transacción que crea el documento**: el Excel solo muestra números ya fijados.
3. Que el número lo digite el usuario después de transmitir: es propenso a errores y no evita huecos ni repetidos.

## Decisión
Opción 2. `rango.ultimo` y el documento se escriben en la misma transacción. Un documento erróneo pasa a `anulado` (con motivo) y su número se queda gastado; aparece en el RESUMEN. Lo transmitido es inmutable; solo se corrige con una nota de ajuste, que usa su propio rango (clase NA). Al llegar a `hasta`, la app no numera y pide un rango nuevo.

## Consecuencias
+ No hay números repetidos y los huecos quedan explicados (anulados).
− Si se anula un número que ya fue transmitido a la DIAN, hay inconsistencia: `anular` exige que el estado sea `generado`.

## Fitness test (`probar_documento_soporte.py`)
- Generar, anular y volver a generar da números consecutivos que no se repiten. Mensaje: «ADR-003: número reutilizado».
- `anular` sobre un documento `transmitido` lanza un error. Mensaje: «ADR-003: transmitido no se anula».
