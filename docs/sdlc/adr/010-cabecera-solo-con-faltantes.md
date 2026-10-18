# ADR-010 · La cabecera ampliada se lee solo cuando falta un número

Estado: aceptado (2026-10-18, aprobado por el usuario)

## Contexto
10 de los 13 omitidos salen bien cortados y se pierden en el número o el tipo; en 5/85387 las piezas miden ≈ 250 px de ancho y el
número es diminuto. R5 (Should) propone recortar arriba, ampliar ×2 y leer solo dígitos. N2 permite +20 % por foto.

## Opciones
1. **Siempre**, en cada pieza: más simple, pero paga en todas las fotos (≈ +5–10 %) y puede cambiar números que ya estaban bien.
2. **Solo cuando `falta` no está vacío**, y solo en las piezas cuya venta no tiene número o tiene uno fuera del nombre.
3. Lector por línea (Tesseract `image_to_data`): más general, pero M de trabajo (R7, Could).

## Decisión
Opción 2, dentro de `relectura.leer_hoja`, antes de cerrar `falta`. Se usa el `leer_digitos` que ya existe sobre el 25 % superior de la
pieza ×2. Solo si aparece **exactamente un** número de `falta`, se asigna; el recibo queda `dudoso` con la nota
«número leído en la cabecera ampliada» y pasa por ④. Se implementa después del registro por pieza (R4): si R4 dice que la causa
dominante es `tipo`, esta decisión se revisa antes de escribir código.

## Consecuencias
+ Costo cero en las fotos completas; peor caso ≈ +8 %. + No toca números ya válidos.
− No rescata un recibo cuya pieza salió con otro `tipo` (eso es R7/R8 o un ajuste del clasificador).

## Fitness test (`probar_relectura.py`, motor y lector simulados que cuentan llamadas)
- Una foto sin faltantes llama 0 veces al lector de cabecera. Mensaje: «ADR-010: cabecera leída sin faltantes».
- Dos faltantes vistos en la misma cabecera → no se asigna ninguno. Mensaje: «ADR-010: número asignado con ambigüedad».
