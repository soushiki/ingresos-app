# 4 · Plan — cierre de caja (01c #2 + #4) · tamaño S

## Summary
Una iteración (≈ 4 h): T1 ajuste cierre > papeles (R1), T2 débito 2815 desde el cierre (R2), T3 respaldo del libro antes de
recalcular (R3), T4 medir septiembre (aceptación e). Todo en `asientos.construir`; cada fila nueva lleva su `fx` (ADR-002) para que
el Excel la calcule igual. Días sin cierre o con cierre sin total/fecha: sin cambios.

## Iteración 1 — el día cuadra con el cierre y 2815 deja de crecer
- [x] T1 (M) Ajuste cierre > papeles — R1, aceptación a/b/d — model: Sonnet — hecho: `construir` suma fila DATOS OCR (bloque «cierre», estado ok) + débito 13809501/crédito 41401501 con fx dato/fila; solo con total_vendido y (cierre escrito o papel de cierre con la fecha del día); papeles > cierre solo avisa; probar_contable +4 checks, suites verdes
  — en `construir`, si el cierre trae `total_vendido` y fecha y supera la venta de los papeles (lo que hoy sale en `cruzar`):
  fila débito 13809501 / crédito 41401501 por la diferencia, descripción «Ajuste al cierre (cierre > papeles)», aviso;
  si los papeles superan al cierre: solo aviso, sin fila. Cada fila con `fx` (dato del cierre − suma de papeles).
  — done when: probar_contable +3 checks: 01-09 (o caso armado) → 4140 suma el cierre, puente con la diferencia, aviso;
  papeles > cierre → filas iguales a hoy + aviso; débito = crédito; sin cierre → filas idénticas a antes; suites verdes.
  — files: `parser_module/contable/asientos.py` (construir, cruzar), `probar_contable.py`
- [x] T2 (M) Débito 2815 desde el cierre — R2, aceptación c/d — model: Sonnet — hecho: `construir` suma 2 filas DATOS OCR (bloque «cierre») + débito 28150502 (propinas_total) y 28150501 (domicilios_pagados − vales, fx `dato − MIN(dato, SUMIFS vales)`, nunca negativo) contra 11050501, «según cierre», solo con fecha de cierre; probar_contable +3 y probar_dia15 +1 (filtro del bloque de efectivo ahora solo grupo «venta»), suites verdes
  — con cierre leído: débito 28150502 por `propinas_total` y débito 28150501 por `domicilios_pagados` menos lo que ya debitaron
  los vales «pago domicilios» del día (nunca negativo, nunca dos veces); crédito 11050501 por la suma. Descripción con «según cierre».
  — done when: probar_dia15 sigue verde (4 vales = 50.000 = cierre → 28150501 debitado una sola vez, 0 desde el cierre);
  probar_contable +3 checks: propinas 48.100 → débito 28150502 48.100; vale 20.000 + cierre 50.000 → 30.000 desde el cierre;
  débito = crédito; suites verdes.
  — files: `parser_module/contable/asientos.py`, `probar_contable.py`, `probar_dia15.py` (solo si cambia lo esperado)
- [ ] T3 (S) Respaldo antes de recalcular — R3 — model: Sonnet
  — antes de la primera escritura de `libro.json` con las reglas nuevas, copiar a `datos/libro.antes-v1.3.0.json` si no existe
  (una sola vez, no se pisa). La exportación ya recalcula y avisa por FIX-6 los días que cambian: verificar que el aviso sale.
  — done when: prueba con libro temporal: primera escritura crea el respaldo idéntico al original; la segunda no lo toca;
  el Excel de un día con cierre > papeles lista el día en «cambió desde que se confirmó».
  — files: `app.py` (`_guardar_libro`), `probar_contable.py` o `probar_revision.py`
- [ ] T4 (S) Medir septiembre — aceptación e — model: Sonnet
  — script de una vez (scratch, no en el repo) sobre una copia de `datos/libro.json`: saldo 2815 antes/después por día y total del mes;
  días con ajuste R1 y su monto; días con aviso papeles > cierre. Anotar el resultado en 06-test-report.
  — done when: saldo 2815 de sept. recalculado ≈ suma de los días sin cierre (o la diferencia explicada) y cada día débito = crédito.
  — files: ninguno del repo (resultado → `docs/sdlc/06-test-report.md` en 6-test)

Orden: T1 → T2 (las dos tocan `construir`, no en paralelo) → T3 → T4. Riesgo: un cierre mal leído mete un ajuste falso → solo con
total y fecha leídos, sale como aviso y el respaldo permite volver.
