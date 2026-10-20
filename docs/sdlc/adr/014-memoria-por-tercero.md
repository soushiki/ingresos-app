# ADR-014 · La cuenta de una salida se recuerda por tercero; las descripciones opacas nunca

Estado: aceptado (2026-10-20, aprobado por el usuario)

## Contexto
R5: el usuario elige la cuenta de las salidas dudosas una vez y la app la recuerda el mes siguiente.
Pero «TRANSFERENCIA CTA SUC VIRTUAL» (≈17,9 M en sept.) no nombra a nadie. Si se recordara, todas esas líneas irían a la misma cuenta.

## Opciones
1. Recordar por la descripción completa: falla con las opacas y con las referencias variables.
2. **Recordar por el tercero normalizado** (la descripción sin el prefijo de la regla, sin dígitos, en mayúsculas y sin tildes). Los prefijos de `sin_tercero` nunca se recuerdan.
3. Recordar por (tercero, rango de valor): más preciso, pero no se puede explicar en una frase.

## Decisión
Opción 2, en `datos/extracto_memoria.json`. Se recuerda solo si el usuario deja marcado «recordar» (marcado por defecto).
Una línea recordada sale con `origen: recordada`, ya tiene su asiento y se puede cambiar. Cambiarla actualiza la memoria hacia adelante, no hacia atrás.

## Consecuencias
+ Después del primer mes, solo las opacas y los terceros nuevos piden elección. − Si un mismo tercero cobra conceptos distintos, le pone la última cuenta: se corrige a mano.

## Fitness test (`probar_extracto.py`)
- Una línea «TRANSFERENCIA CTA SUC VIRTUAL» nunca sale como `recordada`. Mensaje: «ADR-014: descripción opaca recordada».
