# 06 · Test report — extracto bancario, iteración 1 (T1–T5)

## Summary
- **PASS con 1 defecto (FIX-1, no bloquea).** 20/20 suites verdes (`probar_imagen.py` es una herramienta CLI, no suite).
- Cobertura de la iteración: R1 ✓ (513 líneas, 1–23 → 1–30 sin duplicar, hoja/columnas/ZIP/>5 000 filas → error y nada escrito), R2 ✓ (99,6 % vs MOVIMIENTOS, SIN CONCEPTO → revisar), R6 ✓ GMF/rendimientos/Rappi (tarjeta por el neto → T6), R7 ✓ «signo inesperado», R8 ✓ Excel cuadra + grupo «Extracto» + «=» como texto.
- Fuera de esta iteración (por plan): R3 (T11), R4 (T6/T8), R5 (T7/T9/T10), R9 (T12).
- Diff revisado: `8ae2d0b~1..HEAD` (app.py, asientos.py, extracto.py, extracto_reglas.json, contable.html, probar_extracto.py).

## Failures
- Ninguna en las suites.

## Review findings
- **FIX-1 (Should, confirmado):** `clasificar` no es idempotente. Copia los `avisos` y los vuelve a añadir:
  `clasificar(clasificar(L))` da `['signo inesperado', 'signo inesperado']`. Pasa cuando una re-importación trae
  líneas nuevas a un día que ya tenía extracto (se reclasifica el día entero), y pasará en cada reclasificación de T7/T9.
  También deja un aviso viejo si la regla cambia. → `- [ ] FIX-1` en 04-plan, primero de la it. 2.
- Ya anotados en el plan: `_dia` y los otros recalculadores borran `extracto` (T6); «K por revisar» cuenta solo las nuevas (T7/T10).
- Menores, sin tarea: `clasificar(memoria={}, facturas=[])` usa default mutable (no se muta; T7 lo toca igual);
  el error 400 de un .xlsx roto incluye el texto de la excepción de openpyxl (local, aceptable).

## Security review (toca entrada de archivo; exposed: no)
- Tope de 5 MB leído con `read(MAX+1)`, 5 000 filas, openpyxl `read_only`; expat 2.8.5 trae protección contra
  expansión de entidades (billion laughs); XXE no aplica (ElementTree no resuelve entidades externas).
- Nombre del archivo: `basename` y 200 caracteres, solo se guarda en JSON. Descripciones que empiezan con «=» salen como texto en el Excel.
- Riesgo residual bajo: un .xlsx con millones de filas vacías se recorre entero (las vacías no cuentan para el tope). App en 127.0.0.1.

## Load
- NFR: importar un mes < 3 s → real 513 líneas < 3 s (T4). Guardar elección < 300 ms se mide en T9. Sin ramp-load: app local de un usuario.

## Debt check
- Sin linter en el proyecto. `construir` +20 líneas (bloque 5 aislado), ruta nueva ~45 líneas. Sin DEBT nuevo.

## Smoke result (usuario, ≈5 min, en 127.0.0.1:5050 → Contable → ⑤ Extracto)
1. Sube el extracto de septiembre → «513 nuevas, 0 ya estaban · 94 por revisar». (Hecho por el agente en T5 con copia de datos.)
2. Súbelo otra vez → «0 nuevas, 513 ya estaban».
3. Sube cualquier otro .xlsx o una foto → error en rojo, nada cambia.
4. Exporta el Excel → MOVIMIENTOS SEPTIEMBRE trae filas grupo «Extracto» y cada día cuadra.
- Resultado del usuario: pendiente.
