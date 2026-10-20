# SDLC state

project: ingresos_app · vocabulario de medio de pago (01c #8)
goal: Que todo asiento del libro y del Excel use un solo vocabulario de medio de pago (Efectivo / Transferencia / Bre-B / QR / PSE / Tarjeta / Crédito personal / App) y que los asientos que no son de caja (2815, puente, ajustes) lo dejen vacío, como el manual.
size: S      # la columna medio ya existe; es normalizar valores (lectura, libro, Excel) + vaciar en asientos sin caja; sin pantallas nuevas
exposed: no  # app Flask local en 127.0.0.1
regulated: no  # etiqueta interna; no cambia cuentas del PUC ni valores tributarios
next: 5-implement
current task: T2

## Stages
- [x] 0-triage       (confirmado por el usuario 2026-10-19: Tarjeta y Crédito personal se quedan; el libro viejo se normaliza al leer/recalcular, sin migración)
- [~] 1-research     (S: insumo en 01c #8)
- [x] 2-requirements (aprobado 2026-10-19: R1–R4)
- [~] 3-design       (S)
- [x] 4-plan         (T1–T4, 1 iteración ≈ 4–5 h)
- [ ] 5-implement
- [ ] 6-test
- [ ] 7-release
- [ ] 8-maintain     (chequeo mensual 2026-11-17)

## Ciclos anteriores
- Documento soporte, precisión OCR v1.1.0, recibos omitidos v1.2.0, cierre de caja v1.3.0 + v1.3.1, Rappi v1.4.0 → `archive/<ciclo>/`.
- Siguen en su sitio: `01b`, `01c` (insumo de #5/#8), `01d`, `01e`, `01f` (ignorados), `08-maintenance.md`, `adr/`.

## Pendientes
- (hecho 2026-10-19) push de main + tag v1.4.0.
- Usuario: re-subir fotos Rappi de sept. (runbook en `archive/rappi/07-release.md`), actualizar los PC, smoke de v1.3.x.
- Candidatos a ciclo: #5 extracto bancario (M), M-16 lector por línea (M).

## Log
<!-- YYYY-MM-DD | stage | one-line result -->
2026-10-19 | 8-maintain | #6 cerrado (v1.4.0); ciclo Rappi → archive/rappi/ (02, 04, 06, 07, STATE); 08 al día; push pendiente de confirmación
2026-10-19 | 8-maintain | push main + tag v1.4.0 a origin (ff61c7e..2f70187)
2026-10-19 | 8-maintain | revisión: sin ítems nuevos, 08 al día; chequeo mensual 2026-11-17; falta elegir el próximo ciclo (#8 S recomendado)
2026-10-19 | 0-triage | ciclo #8 abierto y confirmado: S, 8 medios (con Tarjeta y Crédito personal), normalizar al leer → 2-requirements
2026-10-19 | 2-requirements | R1–R4 aprobados (Nequi/Daviplata→Transferencia, Mixto→mayor valor, desconocido→vacío+aviso) → 4-plan
2026-10-19 | 4-plan | 04-plan.md: T1 mapa único medio_canonico, T2 asientos (sin caja→vacío, desc conserva Nequi), T3 Mixto + app, T4 libro viejo/R4 → 5-implement
2026-10-19 | 5-implement | T1 hecho: medio_canonico + MEDIOS_CANON + mapa en normalizacion.json, probar_medios 53 checks, 19 suites verdes → T2
