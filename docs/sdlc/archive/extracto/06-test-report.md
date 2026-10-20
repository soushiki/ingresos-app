# 06 · Test report — extracto bancario, iteración 3 (FIX-2, FIX-3, T11–T13)

## Summary
- **PASS: 20/20 suites verdes, review sin defectos que bloqueen.** Los Must del ciclo (R1, R2, R4, R5, R6, R8) están cubiertos desde las it.1–2 y se confirmaron con septiembre real en T13.
- Cobertura de la iteración: R3 ✓ (T11: totales por concepto = MOVIMIENTOS salvo las 2 excepciones de T1; total = suma de Valor), R9 ✓ (T12: deshacer → `construir` de cada día igual a antes), R4/R5 ✓ (FIX-2 invariante `sin_asiento` ⇒ revisar; FIX-3 una factura, una línea).
- Diff revisado: `65bcdc0..HEAD` (app.py +55, extracto.py ±3, contable.html +15, probar_extracto +48 aprox.).

## Failures
- Ninguna (`probar_imagen.py` es un CLI y no una suite).

## Navegador (127.0.0.1:5050, ⑤, ancho 576 px, sobre libro.json real con copia previa)
- Subir septiembre → 513 nuevas · 94 por revisar. «Totales del mes» 2026-09: 14 conceptos, total (total en 01g), «Diferencia digitado vs extracto: Recaudos con tarjetas $ 1». Sin scroll horizontal.
- «Importaciones» lista el archivo y «Deshacer» → «Deshecho: 513 líneas quitadas». Las tarjetas quedan vacías y no hay diferencias.
- Repetido sobre una copia con el cliente Flask: después de deshacer, cada día = el mismo día reconstruido con el código actual (0 diferencias en 1–23).
- libro.json restaurado (mismo sha256 209581d5…). Se borró el `extracto_memoria.json` que creó la prueba.

## Hallazgo para 7-release (no es defecto)
- El libro.json real tiene los días 1–23 de sept. **guardados antes de las reglas de cierre** (v1.3.x; «rige al recalcular», M-17).
  Importar el extracto los recalcula y aparecen filas que hoy faltan: ajuste al cierre 13809501 y pago de propinas y domicilios 2815xx.
  Ejemplo: el débito del 01-sep pasa de cambia (cifras en 01g). Lo cambia el recálculo, no el extracto. Anotarlo en el runbook: hay que avisarle al contador
  y guardar una copia de libro.json antes de la primera importación (esta copia ya existe como `libro.antes-v1.5.0.json`, idéntica).

## Review findings (menores, sin tarea)
- Deshacer libera las facturas enlazadas, pero no reclasifica líneas de otros días que podrían tomarlas. Se corrige al recalcular ese día.
- Deshacer no vuelve a llenar una casilla que se vació con «usar extracto».
- Las líneas que trae de nuevo una segunda subida del mismo archivo siguen siendo de la primera importación. Por eso deshacer la segunda quita 0 líneas.
- «Totales del mes» abre en el mes actual (octubre) y sale vacío. Sería mejor abrir en el último mes con extracto. Es UX y va a 08 si molesta.

## Security review (exposed: no)
- `mes` se valida con una regex y `imp` solo se busca en un dict (404 si no está). DELETE lleva confirm() en la UI y, por venir de otro origen, pide preflight CORS.
- Libro antes que memoria, con tmp + replace y bajo LOCK. La UI arma todo con `el()` y textContent. Sin hallazgos.

## Debt check
- El proyecto no tiene linter. Deshacer reutiliza `_recalcular_dia` y `_dia`, así que no hay lógica duplicada. Sin DEBT.

## Smoke (usuario, ≈5 min, 127.0.0.1:5050 → ⑤ Extracto; antes copiar datos/libro.json)
1. Subir el extracto de septiembre → «513 nuevas … 94 por revisar».
2. «Totales del mes» → elegir septiembre 2026 → total (total en 01g).
3. Asignar una línea en «Por revisar» → la tarjeta desaparece.
4. «Importaciones» → «Deshacer» (o dejarla si ya se va a usar). Si se deshace, «Por revisar» queda vacío.
