# SDLC state

project: ingresos_app · Indra OCR (M-25)
goal: —
size: —
exposed: no  # app Flask local en 127.0.0.1
regulated: —
next: 0-triage
current task: —

## Stages
- [ ] 0-triage
- [ ] 1-research
- [ ] 2-requirements
- [ ] 3-design
- [ ] 4-plan
- [ ] 5-implement
- [ ] 6-test
- [ ] 7-release
- [ ] 8-maintain

## Ciclos anteriores
- Documento soporte, precisión OCR v1.1.0, recibos omitidos v1.2.0, cierre de caja v1.3.0 + v1.3.1, Rappi v1.4.0, medio de pago v1.5.0, extracto bancario v1.6.0 → `archive/<ciclo>/`.
- Siguen en su sitio: `01b`, `01c`, `01d`, `01e`, `01f`, `01g` (ignorados), `08-maintenance.md`, `adr/`.

## Pendientes
- Usuario: smoke de v1.6.0 (`archive/extracto/06-test-report.md`), avisar al contador del recálculo de sept. 1–23 y de las cuentas «por confirmar»; borrar la rama local `respaldo/antes-limpieza-v1.6.0` cuando ya no haga falta.
- Usuario: re-subir fotos Rappi de sept. (runbook en `archive/rappi/07-release.md`), actualizar los PC a v1.6.0, smoke de v1.3.x y v1.5.0 (pasos 1–3 en `archive/medio-de-pago/07-release.md`).
- Candidatos a ciclo: **M-25 Indra OCR (M, absorbe M-16)** — segundo lector R3 + orientación/enderezado, venv 3.14 aparte, licencia OpenRAIL-M. Marcador de renta (`docs/marcador-renta.html`) M-18 perfil fiscal (S) → M-19 NIT por tercero (S–M) → M-20 soporte por gasto + efectivo 771-5 (S) → M-21 impoconsumo bimestral (S) → M-22 pestaña Marcador (M) → M-23 cruce con facturas DIAN (M) → M-24 paquete de cierre (M). Antes de M-18: confirmar con el contador régimen, impoconsumo, ICA y saldos iniciales.

## Log
(log del ciclo #5 → archive/extracto/STATE.md)
2026-10-20 | 8-maintain | #5 cerrado (v1.6.0); ciclo → archive/extracto/ (01–04, 06, 07, STATE); 08 al día; M-25 Indra OCR anotado (absorbe M-16); chequeo mensual 2026-11-17; falta elegir el próximo ciclo (M-25 recomendado o M-18)
2026-10-20 | 8-maintain | usuario elige próximo ciclo: M-25 Indra OCR → next 0-triage
