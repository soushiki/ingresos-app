# SDLC state

project: ingresos_app · cierre de caja (01c #2 + #4)
goal: Que el día del libro cuadre con el cierre de caja: el total del cierre manda (la diferencia con los papeles va a la cuenta puente, con aviso) y el pago de propinas y domicilios debita 2815, para que ese pasivo deje de crecer sin fin.
size: S      # dos reglas en asientos.py sobre datos que ya se leen (cruces, domicilios_pagados, puente 13809501, vales «pago domicilios»); sin pantallas ni datos nuevos
exposed: no  # app Flask local en 127.0.0.1
regulated: no  # cuentas del PUC que ya usa la app; el criterio contable lo confirma el contador, no hay valores tributarios
next: 5-implement

## Stages
- [x] 0-triage       (confirmado por el usuario 2026-10-19)
- [~] 1-research       (S: insumo ya en 01c §2/§4 y 08 M-6/M-7)
- [x] 2-requirements   (aprobado 2026-10-19)
- [~] 3-design         (S)
- [x] 4-plan
- [ ] 5-implement      current task: T4
- [ ] 6-test
- [ ] 7-release
- [ ] 8-maintain

(Mark skipped stages `- [~]`.)

## Ciclos anteriores
- Documento soporte → `archive/documento-soporte/`; precisión OCR v1.1.0 → `archive/precision-ocr/`; recibos omitidos v1.2.0 → `archive/recibos-omitidos/`.
- Siguen en su sitio: `01b`, `01c` (insumo de este ciclo), `01d`, `08-maintenance.md`, `adr/`.

## Punto de partida (de 01c y del código)
- `validar.cruces` ya compara cierre vs. papeles (01-09: el cierre supera a los papeles en ≈ 30 %). La puente 13809501 ya existe (venta sin medio).
- `documentos.py` lee `domicilios_pagados` del cierre; los vales «pago a domicilio» ya van a 28150501 → cuidado con contar el pago dos veces.
- 2815 hoy solo recibe créditos (propina/domicilio causados, también los «en extracto» por M-6).

## Wrong-road check
Lo más barato: no tocar el libro y que el contador haga los dos ajustes a mano en el Excel con el aviso que ya da `cruces`.
Sirve un mes, pero son 30 ajustes por mes y el pasivo 2815 sigue mal en cada exportación; el arreglo en la app es S.

## Log
<!-- YYYY-MM-DD | stage | one-line result -->
2026-10-19 | 0-triage | Ciclo nuevo «cierre de caja» (01c #2 + #4), tamaño S, exposed no, regulated no; ciclo recibos omitidos archivado (archive/recibos-omitidos/). Preguntas: (1) papeles > cierre → solo aviso, sin ajuste [def.]; (2) débito 2815 desde el cierre, sin repetir vales [def.]; (3) rige al recalcular, con respaldo [def.]
2026-10-19 | 0-triage | Confirmado por el usuario: meta y tamaño S; (1) papeles > cierre → solo aviso; (2) débito 2815 desde el cierre sin repetir vales; (3) rige al recalcular, con respaldo → 2-requirements
2026-10-19 | 2-requirements | Borrador 02-requirements.md (R1 cierre manda → puente 13809501, R2 débito 2815 desde el cierre sin repetir vales, R3 recalcular con respaldo); 3 preguntas abiertas; falta aprobación
2026-10-19 | 2-requirements | Aprobado por el usuario con los 3 valores por defecto (domicilios pagados = pago a domiciliarios; propinas_total pagadas el mismo día desde 11050501; diferencia cierre > papeles toda a 41401501) → 4-plan
2026-10-19 | 4-plan | 04-plan.md: 1 iteración ≈ 4 h — T1 ajuste cierre > papeles (R1), T2 débito 2815 desde el cierre (R2), T3 respaldo libro (R3), T4 medir sept. → 5-implement
2026-10-19 | 5-implement | T1 hecho (Sonnet): ajuste cierre > papeles → 13809501/41401501 con aviso; papeles > cierre solo aviso; probar_contable +4, 18/18 verdes. Nota: fx del ajuste es dato fijo en DATOS OCR (no recalcula si se edita una comanda en el Excel)
2026-10-19 | 5-implement | T2 hecho (Sonnet): débito 28150502 por propinas_total y 28150501 por domicilios_pagados − vales del día (fx dato − MIN), crédito 11050501; probar_contable +3, probar_dia15 +1, 18/18 verdes
2026-10-19 | 5-implement | T3 hecho (Sonnet): `_guardar_libro` copia libro.json → datos/libro.antes-v1.3.0.json una sola vez; probar_contable +3 (respaldo idéntico, no se pisa, aviso «cambió desde que se confirmó» ya salía); 18/18 verdes
