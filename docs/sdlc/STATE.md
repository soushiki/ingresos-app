# SDLC state

project: ingresos_app · próximo ciclo por elegir
goal: —
size: —
exposed: no  # app Flask local en 127.0.0.1
regulated: —
next: 0-triage
current task: —  (entre ciclos; M-26 cerrado en v1.9.0)

## Stages
- [ ] 0-triage
- [ ] 1-research
- [ ] 2-requirements
- [ ] 3-design
- [ ] 4-plan
- [ ] 5-implement
- [ ] 6-test
- [ ] 7-release

## Ciclos anteriores
- Documento soporte, precisión OCR v1.1.0, recibos omitidos v1.2.0, cierre de caja v1.3.0 + v1.3.1, Rappi v1.4.0, medio de pago v1.5.0, extracto bancario v1.6.0, Indra OCR v1.7.0, cuenta PUC v1.8.0, recuperar número v1.9.0 → `archive/<ciclo>/`.
- Siguen en su sitio: `01b`…`01h` (ignorados), `08-maintenance.md`, `adr/`.

## Pendientes
- Usuario: smoke de v1.9.0 (4 pasos en `archive/recuperar-numero/06-test-report.md`, ≈ 5 min).
- Contador (no bloquea): contestar `docs/por-confirmar-contador.pdf` (8 decisiones + 5 alias; la 4 ya tiene la mitad del recibo de agua). Al llegar: editar `por_confirmar.json` («estado»: «confirmado», cuenta/alias) y «Reclasificar mes» de cada mes ya guardado.
- Usuario: smoke de v1.6.0 (`archive/extracto/06-test-report.md`), avisar al contador del recálculo de sept. 1–23 y de las cuentas «por confirmar»; borrar la rama local `respaldo/antes-limpieza-v1.6.0` cuando ya no haga falta.
- Usuario: re-subir fotos Rappi de sept. (`archive/rappi/07-release.md`), actualizar los PC a v1.9.0, smoke de v1.3.x y v1.5.0 (pasos 1–3 en `archive/medio-de-pago/07-release.md`).
- POS Ascomp → Vendty (≈ nov. 2026): antes del cambio, preguntar a Ascomp (ascompos@hotmail.com, 3108094441, WhatsApp +57 320 4451364) si exporta ventas pasadas a Excel/CSV. Cuando arranque: fecha exacta, foto de un recibo Vendty, documentación de su «Api de integración» y si el plan la incluye → posible ciclo «importar ventas Vendty» (S–M). Preguntar al contador por qué se pasó a POS electrónico (afecta M-18).
- Candidatos a ciclo: Marcador de renta (`docs/marcador-renta.html`) M-18 perfil fiscal (S) → M-19 NIT por tercero (S–M) → M-20 soporte por gasto + efectivo 771-5 (S) → M-21 impoconsumo bimestral (S) → M-22 pestaña Marcador (M) → M-23 cruce con facturas DIAN (M) → M-24 paquete de cierre (M). Antes de M-18: confirmar con el contador régimen, impoconsumo, ICA y saldos iniciales. Deuda chica: 2 notas de M-27 It. 3 en 08.
- Chequeo mensual (08): 2026-11-17.

## Log
(log del ciclo #8 recuperar número → archive/recuperar-numero/STATE.md)
2026-10-26 | 8-maintain | M-26 cerrado (v1.9.0); ciclo → archive/recuperar-numero/ (02, 04, 06, 07, STATE); 08 al día (resumen v1.9.0, fila M-26 cerrada); falta smoke del usuario; próximo ciclo por elegir (M-18 tras confirmar con el contador, o Vendty cuando llegue)
