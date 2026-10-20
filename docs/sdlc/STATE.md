# SDLC state

project: ingresos_app · vocabulario de medio de pago (01c #8)
goal: Que todo asiento del libro y del Excel use un solo vocabulario de medio de pago (Efectivo / Transferencia / Bre-B / QR / PSE / Tarjeta / Crédito personal / App) y que los asientos que no son de caja (2815, puente, ajustes) lo dejen vacío, como el manual.
size: S      # la columna medio ya existe; es normalizar valores (lectura, libro, Excel) + vaciar en asientos sin caja; sin pantallas nuevas
exposed: no  # app Flask local en 127.0.0.1
regulated: no  # etiqueta interna; no cambia cuentas del PUC ni valores tributarios
next: 8-maintain
current task: —

## Stages
- [x] 0-triage       (confirmado por el usuario 2026-10-19: Tarjeta y Crédito personal se quedan; el libro viejo se normaliza al leer/recalcular, sin migración)
- [~] 1-research     (S: insumo en 01c #8)
- [x] 2-requirements (aprobado 2026-10-19: R1–R4)
- [~] 3-design       (S)
- [x] 4-plan         (T1–T4, 1 iteración ≈ 4–5 h)
- [x] 5-implement
- [x] 6-test         (2.ª pasada: verde; smoke manual 1–3 del usuario pendiente)
- [x] 7-release      (v1.5.0 publicada)
- [ ] 8-maintain     (chequeo mensual 2026-11-17)

## Ciclos anteriores
- Documento soporte, precisión OCR v1.1.0, recibos omitidos v1.2.0, cierre de caja v1.3.0 + v1.3.1, Rappi v1.4.0, medio de pago v1.5.0 → `archive/<ciclo>/`.
- Siguen en su sitio: `01b`, `01c` (insumo de #5/#8), `01d`, `01e`, `01f` (ignorados), `08-maintenance.md`, `adr/`.

## Pendientes
- (hecho 2026-10-19) push de main + tag v1.4.0.
- (hecho 2026-10-20) push de main + tag v1.5.0.
- Usuario: re-subir fotos Rappi de sept. (runbook en `archive/rappi/07-release.md`), actualizar los PC a v1.5.0, smoke de v1.3.x y v1.5.0 (pasos 1–3 en `archive/medio-de-pago/07-release.md`).
- Candidatos a ciclo: #5 extracto bancario (M), M-16 lector por línea (M).

## Log
<!-- YYYY-MM-DD | stage | one-line result -->
(log del ciclo #8 → archive/medio-de-pago/STATE.md)
2026-10-19 | 8-maintain | revisión: sin ítems nuevos, 08 al día; chequeo mensual 2026-11-17; falta elegir el próximo ciclo (#8 S recomendado)
2026-10-20 | 7-release | push main + tag v1.5.0 a origin (550907b..c7da075)
2026-10-20 | 8-maintain | #8 cerrado (v1.5.0); ciclo → archive/medio-de-pago/ (02, 04, 06, 07, STATE); 08 al día; sin ítems nuevos; chequeo mensual 2026-11-17; falta elegir el próximo ciclo (#5 o M-16)
