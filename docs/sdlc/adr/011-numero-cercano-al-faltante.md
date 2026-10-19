# ADR-011 · Un número a una cifra de un solo faltante se le asigna (reemplaza ADR-010)

Estado: aceptado (2026-10-19, aprobado por el usuario) · reemplaza ADR-010

## Contexto
T11 implementó ADR-010 (Tesseract sobre la cabecera ×2) y `medir --completo` dio 0 rescatados (omitidos 15/103): las fotos miden
≈ 1100 px con 6 recibos y el número no se lee ni a ×3/×4; además vio 85446 en la pieza del 85444. Pero qwen casi acierta:
65340, 05339, B5442, 85188, 85598 en vez de 85340, 85339, 85442, 85388, 85588.

## Opciones
1. Seguir con Tesseract (más ampliación, foto original): no hay más píxeles que leer.
2. qwen sobre la cabecera ampliada: una llamada más por pieza sospechosa (≈ 15 s), resultado sin medir (spike).
3. **Cercanía:** el número leído (el del documento o el crudo tras «RECIBO #», con B→8, O→0, S→5) a ≤ 1 cifra de **exactamente un**
   faltante de la foto, con la misma cantidad de cifras → se asigna.

## Decisión
Opción 3, en `relectura.leer_hoja`, después de re-segmentar y antes de los vecinos; solo en ventas cuyo número no está en el nombre.
El recibo queda `dudoso` con la nota CABECERA («Número corregido por cercanía al nombre…») y pasa por ④. Sin faltantes no hace nada.
El usuario acepta ≈ 5/103 omitidos por ahora; la meta N3 (≤ 2 %) queda abierta.

## Consecuencias
+ Costo de tiempo cero (sin OCR nuevo). + Medido sobre los informes T10/T11: rescata 8/13 y 9/15, 0 asignaciones falsas.
− No rescata piezas sin número legible (85387/389/390, 85375, 85411). − Un error de 1 cifra hacia otro faltante sería ambiguo → no asigna.

## Fitness test (`probar_relectura.py`)
- Una foto sin faltantes no cambia ningún número. Mensaje: «ADR-011: número cambiado sin faltantes».
- Un número a 1 cifra de dos faltantes → no se asigna ninguno. Mensaje: «ADR-011: número asignado con ambigüedad».
