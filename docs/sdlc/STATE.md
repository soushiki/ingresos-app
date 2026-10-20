# SDLC state

project: ingresos_app · mantenimiento (sin ciclo abierto)
goal: Mantener la app sana; cada pedido nuevo abre un ciclo desde 0-triage.
size: -
exposed: no  # app Flask local en 127.0.0.1
regulated: no
next: 8-maintain

## Stages
- [x] 0–7 ciclo Rappi (v1.4.0) → `archive/rappi/`
- [ ] 8-maintain   (en curso; chequeo mensual 2026-11-17)

## Ciclos anteriores
- Documento soporte, precisión OCR v1.1.0, recibos omitidos v1.2.0, cierre de caja v1.3.0 + v1.3.1, Rappi v1.4.0 → `archive/<ciclo>/`.
- Siguen en su sitio: `01b`, `01c` (insumo de #5/#8), `01d`, `01e`, `01f` (ignorados), `08-maintenance.md`, `adr/`.

## Pendientes
- (hecho 2026-10-19) push de main + tag v1.4.0.
- Usuario: re-subir fotos Rappi de sept. (runbook en `archive/rappi/07-release.md`), actualizar los PC, smoke de v1.3.x.
- Candidatos a ciclo: #8 vocabulario de medio de pago (S), #5 extracto bancario (M), M-16 lector por línea (M).

## Log
<!-- YYYY-MM-DD | stage | one-line result -->
2026-10-19 | 8-maintain | #6 cerrado (v1.4.0); ciclo Rappi → archive/rappi/ (02, 04, 06, 07, STATE); 08 al día; push pendiente de confirmación
2026-10-19 | 8-maintain | push main + tag v1.4.0 a origin (ff61c7e..2f70187)
