# ADR-007 · La referencia es una copia congelada y medir nunca escribe el libro

Estado: aceptado (2026-10-18, aprobado por el usuario)

## Contexto
R9 necesita una cifra de precisión antes y después de cada cambio. Los ≈227 recibos corregidos de septiembre son la verdad conocida. El usuario pidió releer septiembre solo como prueba, sin tocar lo corregido.

## Opciones
1. Medir directo contra `libro.json`: siempre al día, pero una edición posterior cambia la vara y no se puede comparar un antes con un después; y un error del script podría escribir el libro.
2. **Copia congelada en `datos/referencia/referencia_<mes>.json`** (documentos corregidos + ruta de su foto + fecha de congelado), a la que R8 agrega cada recibo confirmado.

## Decisión
Opción 2. `medir_precision.py` lee la referencia y las fotos, relee con `leer_recibo` y escribe solo su informe (`datos/referencia/informes/<fecha-hora>.json`). Se compara por número de recibo; el que no aparece cuenta como omitido. «Validado con error» = estado validado y algún campo distinto de la referencia.

## Consecuencias
+ Cada cambio se juzga contra la misma vara (N3). + La misma copia sirve para exportar el conjunto de entrenamiento (R10).
− Si se corrige un recibo viejo en el libro, la referencia no se entera hasta que se vuelva a congelar (acción explícita).

## Fitness test (`probar_precision.py`)
- Correr la medición sobre una referencia de prueba deja `libro.json` con la misma sha256. Mensaje: «ADR-007: la medición tocó el libro».
