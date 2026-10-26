# ADR-019 · La cuenta va por ítem y DATOS OCR trae una fila por (papel, cuenta)

Estado: aceptado (2026-10-25, aprobado por el usuario)

## Contexto
R3 pide repartir una factura con ítems de varias cuentas, y R8 pide un renglón por cuenta en el export. Hoy un papel tiene una sola `cuenta`, y `asientos.construir` arma 1 débito y 1 crédito por papel desde DATOS OCR (DEBT-1, con fórmulas SUMIFS por ADR-002).

## Opciones
1. **Repartir en `construir`**: DATOS OCR sigue con una fila por papel y el asiento se reparte por dentro. Las fórmulas del Excel ya no cuadran con DATOS OCR, porque no hay una fila por cuenta que sumar.
2. **Un papel por ítem**: partir la factura en N documentos. Rompe la numeración, los duplicados y el «revisado».
3. **Una fila de DATOS OCR por (papel, cuenta)**, con `valor` = suma de los ítems de esa cuenta, más una fila «diferencia ítems vs total» a la puente si `|dif| > 1`. La caja menor ya agrupa por cuenta con SUMIFS. La factura agrupa sus filas por `id`: N débitos y 1 crédito por el total.

## Decisión
Opción 3. `doc.cuenta` se queda como la cuenta del ítem de mayor valor (expand→contract). Las ventas no cambian: la cuenta de cada fila sigue saliendo del medio de pago (R1, origen).

## Consecuencias
+ El export y «BALANCE x CTA» no cambian de código. Las fórmulas siguen sumando DATOS OCR.
+ Un papel de una sola cuenta da exactamente las mismas filas que hoy.
− DATOS OCR crece un poco (≈ +10 % de filas en gastos). La columna `Id` se repite dentro de un papel.

## Fitness tests (`probar_contable.py`)
- En todos los días de `datos/libro.json` (y en los ejemplos), para cada papel de gasto: Σ débitos de su `id` = crédito de su `id`. Mensaje: «ADR-019: papel repartido no cuadra».
- Un papel cuyos ítems van a una sola cuenta da las mismas filas de MOVIMIENTOS que en v1.7.0. Mensaje: «ADR-019: cambió el asiento de un papel de una cuenta».
- Una factura con ítems que no suman el total tiene una fila con la cuenta `puente_gasto` y el aviso «diferencia ítems vs total». Mensaje: «ADR-019: diferencia sin puente».
