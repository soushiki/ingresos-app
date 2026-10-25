# 06 · Test report — M-27 Iteración 2, re-smoke tras FIX-1…3 + DEBT-2 (`28500bd..aa999b4`)

## Summary
- **PASA.** Suite 25/25 verde. Los 3 bugs que ponían una cuenta equivocada están arreglados, cada uno con su check, y el smoke sobre una copia del libro de sept. salió bien. Los Musts de It. 2 cumplen → It. 3 (T9–T12).
- Cobertura de It. 2: R1, R2, R3, R5 y R8 siguen cubiertos, igual que en la primera pasada (`probar_motor`, `probar_items`, `probar_datos_ocr`, fitness ADR-019 en `probar_contable`).
- Cada «done when» de los FIX tiene su check:
  - FIX-1: `probar_motor:150-158` (cuenta elegida → recalcular → sigue; ninguna salida es «True») y `probar_items:46` (forma booleana real).
  - FIX-2: `probar_motor:211-228` (vale → puente → «hielo» → 14050502; cambio de tipo o valor rehace los ítems; lo manual no cambia).
  - FIX-3: `probar_items:53` (olivas, granito, activa) y `probar_datos_ocr` (0,24 % sin fila puente, D = C).
  - DEBT-2: `probar_motor:233-242` (cambia el mtime → recarga; sin cambio → mismo MOTOR).

## Failures (suite)
- Ninguna. `probar_motores_falso.py` (trabajador falso) y `probar_imagen.py` (CLI) no son tests.

## Review (diff de los FIX: 4 archivos de código, +48/−6)
Sin bugs bloqueantes. Hay 3 notas, todas ya conocidas o fuera de alcance:
1. Si el papel tiene varios ítems y el usuario elige una cuenta a mano, esa cuenta va a todos los ítems. Corregir un solo ítem es T9.
2. Los papeles viejos sin `items_huella` la graban en su primera pasada, así que un cambio anterior a esa pasada no rehace sus ítems. El botón «Reclasificar mes» (T10) cubre ese caso.
3. Si se quita la cuenta a mano de un papel, sus ítems siguen marcados `manual`. La interfaz de hoy no tiene ese camino; revisarlo en T11 cuando la cuenta se edite por ítem.
- `por_cuenta` ya ordena de mayor a menor, así que la diferencia ≤ 1 % sí se suma al ítem mayor.
- El nuevo `_motor_vigente` hace solo 4 `stat` por llamada, un costo despreciable para N3.

## Seguridad
`exposed: no` (127.0.0.1). Los FIX no agregan endpoints ni entradas nuevas. `_motor_vigente` solo lee archivos propios de `parser_module/contable/`.

## Debt
El proyecto no tiene linter. Los cambios son pequeños y no hace falta una tarea DEBT nueva.

## Smoke (2026-10-25)
Se usó el cliente de pruebas de Flask con `POST /api/contable/asientos` sobre una copia en memoria de `datos/libro.json`. No se guardó nada.
1. Sept., 30 días: 0 descuadres. El 2026-09-10 hay un papel con 2 cuentas, que sale en 2 filas de DATOS OCR (51352501 + puente con aviso) ✓
2. Cuenta a mano 51350501 en un gasto → recalcular dos veces → sigue en 51350501 ✓
3. Vale sin detalle → puente; se escribe «hielo» → 14050502 ✓
4. BALANCE x CTA de sept.: el fitness R8 de `probar_contable` lo da igual al de antes (D = C) ✓
- No se hizo el click-through en el navegador para no escribir en el libro real. Queda opcional para el usuario: los pasos 2–3 en la pestaña Contable.
