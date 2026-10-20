# ADR-012 · Extracto guardado en el día del libro; casillas «banco» derivadas, no reescritas

Estado: aceptado (2026-10-20, aprobado por el usuario)

## Contexto
Los recaudos de venta ya entran al libro por las casillas `banco` digitadas (09-01..09-23). El extracto trae esas mismas
entradas. R4 exige que no se cuenten dos veces; P1 dice que el extracto llena las casillas y muestra la diferencia si no cuadran.
El NFR pide que importar sea todo o nada y que el recálculo sea determinista.

## Opciones
1. Archivo aparte `datos/extracto.json` + escribir los valores en `banco`: son dos escrituras (no atómicas) y deshacer (R9) obliga a recordar qué casilla tocó el extracto.
2. SQLite para el extracto: es transaccional, pero el libro sigue en JSON y la importación no queda atómica entre los dos.
3. **Las líneas van en `libro[fecha]["extracto"]` y la casilla efectiva se calcula en `construir()`:** la digitada si es > 0, si no la suma del extracto para ese medio.

## Decisión
Opción 3. Importar o deshacer = una sola llamada a `_guardar_libro` (tmp + replace, con copia previa).
La casilla digitada nunca se pisa en silencio. La diferencia por medio se informa, y «usar extracto» borra la digitada.

## Consecuencias
+ Es atómico, determinista y R9 queda trivial (se filtra por `imp`). + No hay migración: los días sin `extracto` funcionan igual.
− libro.json crece ≈1,5 MB al año y cada elección lo reescribe entero (está bien hasta ≈10 MB; después, SQLite).

## Fitness test (`probar_extracto.py`)
- Un día con la casilla qr digitada y líneas RECAUDO QR en el extracto da una sola fila de débito 11200501 de QR. Mensaje: «ADR-012: recaudo contado dos veces».
- Importar, deshacer y recalcular deja las filas idénticas a las de antes. Mensaje: «ADR-012: deshacer no restaura el día».
