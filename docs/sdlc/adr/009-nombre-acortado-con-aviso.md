# ADR-009 · Un número acortado del nombre se corrige por sufijo y siempre se avisa

Estado: aceptado (2026-10-18, aprobado por el usuario)

## Contexto
«85334-338 al 3341-343» da `None` hoy: «3341» se completa a 93341, fuera del rango, y la foto se corta en 1 pieza callada (2 omitidos).
La referencia confirma que la foto trae 85334, 85338–85341 y 85343 (6 papeles). Requisitos: R3 (Must) y «no adivinar sin avisar» (Won't).

## Opciones
1. **Rechazar** el nombre (`None`) pero avisar «no entiendo el nombre»: seguro, pero esta foto sigue en 1 pieza.
2. **Adivinar en silencio**: arregla esta foto y esconde los errores de digitación.
3. **Corregir por sufijo con aviso**: si un número acortado cae fuera de `[anterior, anterior+30]`, probar sus últimas k−1, k−2 … (≥ 2)
   cifras; la primera que cae en rango gana y queda en `correcciones` («3341 → 85341»). Si ninguna cae, `None` + aviso.

## Decisión
Opción 3, en `validar.leer_nombre` (pura). `numeros_de_nombre` la envuelve y no cambia para los demás llamadores. La corrección viaja
como aviso del primer recibo de la foto; un nombre con dígitos que no se entiende crea un marcador «No entiendo el nombre de la foto X»
(ADR-008) para que ④ lo muestre.

## Consecuencias
+ Recupera 85340 y 85343 sin tocar el OCR. + Nada se arregla sin dejar rastro.
− Una corrección por sufijo puede ser la equivocada; el aviso y R5 de `validar` (número fuera del nombre) lo delatan.

## Fitness test (`probar_validar.py`)
- `numeros_de_nombre("85334-338 al 3341-343.jpg") == [85334, 85338, 85339, 85340, 85341, 85343]` y `leer_nombre(…).correcciones`
  no está vacío. Mensaje: «ADR-009: corrección de nombre sin aviso o lista mal».
- Los nombres de las pruebas actuales dan lo mismo que antes. Mensaje: «ADR-009: leer_nombre cambió un nombre que ya se entendía».
