# 6 · Test report — cierre de caja (v1.3.0)

## Summary
**PASA.** R1, R2 y R3 (todos Must) cubiertos y verdes; aceptación a–e cumplida. 18/18 suites verdes (`probar_imagen.py` es
herramienta manual, pide una imagen). Diff de la iteración (86e816d..HEAD): `asientos.py` +44, `app.py` +2, pruebas +56.
Sin defectos que bloqueen; 2 notas de revisión → 08-maintenance (M-17). → 7-release.

## Cobertura (Given/When/Then → prueba)
- (a) cierre > papeles → 4140 = cierre, puente con la diferencia, aviso: `probar_contable` R1 (caso armado 200.000 vs 80.000; también con el total del papel de cierre). Caso real 01-09 en T4.
- (b) papeles > cierre → filas iguales + aviso; sin cierre o cierre de otra fecha → sin ajuste: `probar_contable` R1.
- (c) vale 20.000 + cierre 50.000 → 30.000 desde el cierre; vales = cierre → nada desde el cierre: `probar_contable` R2, `probar_dia15`.
- (d) débito = crédito y cada fila nueva con `fx`: `probar_contable` R1/R2; 30/30 días de sept. en T4.
- (e) 2815 deja de crecer: T4 abajo. R3 respaldo único, no se pisa, aviso «cambió desde que se confirmó»: `probar_contable` R3.

## Failures
Ninguna.

## Review findings (revisión del diff, sin `/security-review`: exposed no, no toca entrada, auth ni secretos)
- Bajo · el `fx` del ajuste R1 es dato fijo en DATOS OCR: si el contador corrige una comanda en el Excel, el ajuste no se recalcula
  (sí lo hace el de domicilios R2). Aceptado en T1; anotado como M-17.
- Bajo · la suma de consumo de los papeles se calcula 3 veces en `construir` (R1 y el aviso papeles > cierre); y una cortesía con
  consumo cuenta en «papeles» aunque no entra a 4140 → el ajuste quedaría corto por esa cortesía. Ningún caso en sept. (0 avisos). M-17.
- Fórmula R2 en Python y Excel coinciden (vales = bloque «caja», cuenta 28150501, solo efectivo; MIN evita negativos).

## Debt
Sin linter. `construir` crece 44 líneas (dos bloques con `if`); sin tarea DEBT, solo la nota M-17.

## T4 — Medir septiembre (aceptación e) — copia de datos/libro.json, 30 días
- Saldo 2815 del mes: baja ≈ 21 %. Días sin cierre (23): iguales (≈ 97 % del saldo nuevo). Días con cierre (7): su aporte baja ≈ 86 %.
- Residuo (≈ 3 % del saldo nuevo) = días donde el pago del cierre no cubre lo causado: 20 y 30-sep por encima; 01, 06, 29 y 07 por debajo; 17-sep en 0.
- Ajuste R1 en 5 días al puente 13809501: 01, 06, 07, 20 y 29-sep (el 20-sep es el mayor, ≈ 46 % del mes). Avisos papeles > cierre: 0.
- Débito = crédito en 30/30 días. Los días con R1 suben su total (20-sep ≈ +14 %) → salen en «cambió desde que se confirmó».

## Smoke (≈ 5 min, lo hace el usuario; crea el respaldo real)
1. `python app.py` → ③ Contable, abrir 01-09 y recalcular: aviso «Ajuste al cierre …», 4140 suma el total del cierre.
2. Ver que existe `datos/libro.antes-v1.3.0.json` (copia de antes).
3. En el mismo día: fila «Pago de propinas según cierre» (28150502) y débito = crédito.
4. Exportar el Excel de septiembre: hoja de cambios lista 01, 06, 07, 20 y 29-sep; MOVIMIENTOS cuadra.
Resultado: pendiente del usuario.
