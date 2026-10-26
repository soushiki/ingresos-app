# 06 · Test report — M-27 Iteración 3 (`d2eeaa9..2aea379`: T9–T12 + decisión 4)

## Summary
- **PASA.** Suite 26/26 verde (exit 0 cada archivo). Los Musts de It. 3 (R6, R7) y el Should R10 tienen su check o su entregable. Es la última iteración del plan → 7-release (v1.8.0).
- Cobertura por R-id:
  - **R6** corregir un ítem → `manual`, se aprende y el siguiente igual sale «enseñado»; el proveedor solo se enseña si todos los ítems van a la misma cuenta: 10 checks T9 en `probar_motor.py`. La UI («Cuenta por ítem») la probó en el navegador (puerto 5070).
  - **R7** vista previa antes → después, solo aplica con la huella, lo manual no cambia, idempotente, sept. < 30 s: `probar_reclasificar.py` (huella alterada o día guardado entre plan y aplicar → `HuellaDistinta` y libro intacto; cuenta a mano e ítem manual intactos; 2.º plan = 0 cambios; endpoint 400/409; días que cambian débito/ingresos). Sept. real: plan 0,08 s + aplicar 0,11 s (N3).
  - **R10** `docs/por-confirmar-contador.pdf` (8 decisiones + 5 alias R4, regla usada, filas del manual e ítems del libro por punto); contestar = editar `por_confirmar.json` (la decisión 4 ya se contestó así, sin tocar la lógica).
- Ya en uso real: «Reclasificar mes» se aplicó a sept. tras la respuesta del contador (D = C = 62.056.359) y la decisión 4 movió 1 ítem (10/09 «Agua fría»).

## Failures (suite)
- Ninguna.
- `probar_motores_falso.py` (trabajador falso) y `probar_imagen.py` (CLI) no son tests.

## Review (diff de código: app.py, clasificar.py, reclasificar.py, contable.html, por_confirmar_pdf.py; +551/−18 con tests)
Sin bugs que pongan una cuenta equivocada. Notas, ninguna bloquea:
1. `POST /api/contable/aprender` con `item` numérico y **sin** `documento` enseña la palabra «0», «1»… La UI siempre manda `documento`, así que no pasa hoy. Arreglo de 1 línea (400 si `item` es número sin `documento`) → `08-maintenance`.
2. En `reclasificar._dias`, si FIX-2 rehízo los ítems de un papel, «antes» se toma por índice y puede mostrar una cuenta de otro ítem en la vista previa. Solo afecta el texto de la vista; lo que se aplica sale del motor.
3. Aplicar rehace el día entero con `construir`, así que también entran reglas de ciclos anteriores (sept.: 09-01, 09-17, 09-20). Ya se ve en la vista previa (`dias`) antes de Aplicar; es lo que pidió el usuario.
4. `FRASES` ahora busca por palabra completa: «agua» ya no toca «aguacate» ni «aguardiente». `FRASES_PROVEEDOR` deja que el nombre de la empresa de servicios baste.
- El rastro `reclasificaciones[]` va por día y el respaldo `libro.antes-v1.8.0.json` se hace una sola vez (no se pisa).

## Seguridad
`exposed: no` (127.0.0.1). Endpoint nuevo `reclasificar`: valida mes `AAAA-MM`, huella 64 hex, cuerpo ≤ 4 KB, todo bajo `LOCK`, días con DS transmitido no se tocan. La UI arma la tabla con DOM/`textContent` (sin `innerHTML` con datos); el resto usa `esc()`.

## Debt
El proyecto no tiene linter. `reclasificar.py` es corto (109 líneas, funciones pequeñas). No hace falta una tarea DEBT nueva.

## Smoke
- Hecho en It. 3 (T11, navegador puerto 5070, copia de sept.): vista previa, Aplicar (22 días, 2.ª vista nada, D = C), cuenta por ítem → «Aprendido», teléfono/tablet sin scroll lateral. Luego en el libro real con la respuesta del contador.
- Pendiente opcional para el usuario (≈ 5 min, en la pestaña Contable):
  1. «Reclasificar mes» con 2026-09 → debe decir que no hay cambios (sept. ya está reclasificado).
  2. Abrir un papel de compra con varios ítems → cambiar la cuenta de uno → toast «Aprendido».
  3. Abrir `docs/por-confirmar-contador.pdf` y ver las 8 decisiones y la tabla de 5 alias.
