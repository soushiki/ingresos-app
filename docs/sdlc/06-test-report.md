# 06 · Test report — M-27 Iteración 2 (T6–T8, `da95a24..fc3af3e`)

## Summary
- **FALLA**: la suite está verde, pero la revisión encontró 3 bugs que ponen una cuenta equivocada en los libros (`regulated: yes`). Reproducidos a mano el 2026-10-25.
- Cobertura de R-ids de It. 2:
  - R1 (origen comanda) ✓ `probar_motor`; la contrapartida por medio ya estaba en `probar_medios`.
  - R2 ✓ `probar_items`, más un check nuevo en 6-test: el gasto del cierre llega como ítem del vale.
  - R3 ✓ `probar_datos_ocr` (N débitos + 1 crédito, diferencia de más y de menos); lo de PUC y alias está en T4.
  - R5 (capas y motivo) ✓ `probar_motor`; lo de «manual», reclasificar e idempotencia es de It. 3.
  - R8 ✓ fitness ADR-019 en `probar_contable`: sept., 30 días, mismo BALANCE x CTA, D = C = 62.833.386.
- **N3**: un día de sept. (90 papeles) tarda 0,013 s, bajo el límite de 1 s. No hace falta prueba de carga, porque la app es local y de un solo usuario.

## Failures (suite)
- Ninguna: 25/25 `probar_*.py` verdes. `probar_motores_falso.py` (trabajador falso, M-28) y `probar_imagen.py` (CLI) no son tests.

## Review findings (`/code-review` high, 8)
1. **FIX-1** `clasificar_doc` pisa `doc.cuenta` con la del ítem mayor en cada pasada. La cuenta que el usuario elige en la tarjeta (`contable.html:280`) se pierde en el siguiente `recalcular`. Reproducido: 51350501 → 14050502.
2. **FIX-2** `items_de` usa `cuenta_manual` como código, pero la app lo guarda como booleano. Un papel viejo con cuenta a mano sale con la cuenta «True» por la capa manual (no pasa por la puente). Reproducido. El test `probar_items.py:43` usa la forma equivocada.
3. **FIX-3** Un ítem que fue a la puente no se reclasifica nunca, aunque luego llegue el detalle (usuario, o cierre posterior vía `completar_desde_cierre`). Antes de T8, todo papel sin cuenta se volvía a clasificar. Reproducido.
4. **FIX-4** Cambiar el tipo, el proveedor o el valor de un papel deja los ítems viejos (clasificados con otro origen o con valor viejo).
5. **FIX-5** `_NO_ITEM` filtra por subcadena («iva» en «olivas», «nit» en «granito»). Se pierde el ítem y la factura no se reparte.
6. **FIX-6** En un papel repartido, una diferencia > 1 peso pero ≤ 1 % va a la puente y a revisión, aunque `items_de` ya aceptó la suma. Umbral: usar el mismo ±1 %.
7. DEBT: `MOTOR` no se recarga si cambian `terceros_cuentas.json`, `por_confirmar.json` o `modelo_manual.json` (T12 «contestar = editar el JSON»); hay que reiniciar la app.
8. Test: el caso de migración de `probar_items` usa la forma equivocada (va con FIX-2).

## Seguridad
`exposed: no` (127.0.0.1). It. 2 no agrega endpoints. La entrada nueva es el texto OCR local que lee `_items_texto`, con montos acotados (100 ≤ v < 5.000.000). El regex de líneas es perezoso pero lineal en la práctica (una línea OCR). No se tocan secretos ni auth. `/aprender` ya valida la cuenta contra `CATALOGO`.

## Debt
Sin linter en el proyecto. `asientos.construir` bloque 4 creció (listas `js`/`jm`): legible, sin tarea DEBT aparte salvo el punto 7.

## Smoke (pendiente, tras FIX-1…4)
1. Abrir la app → Contable → un día de sept. con una factura de 2 cuentas: ver 2 filas en DATOS OCR y el asiento cuadrado.
2. Cambiar a mano la cuenta de un gasto → «Recalcular» → la cuenta elegida sigue.
3. Un vale sin detalle (en la puente) → escribir «hielo» → pasa a 14050502.
4. Exportar el Excel de sept. → BALANCE x CTA igual al de antes en los papeles de una sola cuenta.
