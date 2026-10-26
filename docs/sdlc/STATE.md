# SDLC state

project: ingresos_app · (sin ciclo abierto: elegir el próximo)
goal: —
size: —
exposed: no  # app Flask local en 127.0.0.1
regulated: yes  # cuentas PUC y renta: decisiones del contador
next: 0-triage
current task: v1.8.0 publicada y M-27 cerrado; elegir ciclo (M-26 recomendado, o M-18)

## Stages
- [ ] 0-triage

## Ciclos anteriores
- Documento soporte, precisión OCR v1.1.0, recibos omitidos v1.2.0, cierre de caja v1.3.0 + v1.3.1, Rappi v1.4.0, medio de pago v1.5.0, extracto bancario v1.6.0, Indra OCR v1.7.0, cuenta PUC v1.8.0 → `archive/<ciclo>/`.
- Siguen en su sitio: `01b`…`01h` (ignorados), `08-maintenance.md`, `adr/`.

## Pendientes
- Contador (no bloquea): contestar `docs/por-confirmar-contador.pdf` (8 decisiones + 5 alias; la 4 ya tiene la mitad del recibo de agua). Al llegar: editar `por_confirmar.json` («estado»: «confirmado», cuenta/alias) y «Reclasificar mes» de cada mes ya guardado (la vista previa muestra lo que cambia).
- Usuario: smoke de v1.6.0 (`archive/extracto/06-test-report.md`), avisar al contador del recálculo de sept. 1–23 y de las cuentas «por confirmar»; borrar la rama local `respaldo/antes-limpieza-v1.6.0` cuando ya no haga falta.
- Usuario: re-subir fotos Rappi de sept. (runbook en `archive/rappi/07-release.md`), actualizar los PC a v1.6.0, smoke de v1.3.x y v1.5.0 (pasos 1–3 en `archive/medio-de-pago/07-release.md`).
- Nuevo (2026-10-20): el POS es Ascomp; pasa a Vendty el mes que viene (≈ nov. 2026, aún no instalado), así que todo lo de hoy es Ascomp y M-25 sigue igual. Antes del cambio: preguntar a Ascomp (ascompos@hotmail.com, 3108094441, WhatsApp +57 320 4451364; tiene login en nube.ascomp-pos.com) si se pueden exportar las ventas pasadas a Excel/CSV; su web no documenta informes ni formato del recibo. Cuando arranque: fecha exacta, una foto de un recibo Vendty y pedir a Vendty la documentación de su «Api de integración» (sí existe, está en su web) y si el plan la incluye; con API o export Excel/CSV, posible ciclo «importar ventas Vendty» (S–M) en vez de OCR para los días nuevos. Abecé DIAN (feb. 2025): el tiquete POS es documento equivalente que la DIAN valida; persona natural no responsable de IVA/INC no está obligada salvo > 3.500 UVT → preguntar al contador por qué se pasó a POS electrónico (afecta M-18).
- Candidatos a ciclo (falta elegir): **M-26 recuperar número con Indra (S–M)** — usar los números que Indra ve en el recorte cuando qwen no da el número (omitidos 5/103 → ≤ 2). Marcador de renta (`docs/marcador-renta.html`) M-18 perfil fiscal (S) → M-19 NIT por tercero (S–M) → M-20 soporte por gasto + efectivo 771-5 (S) → M-21 impoconsumo bimestral (S) → M-22 pestaña Marcador (M) → M-23 cruce con facturas DIAN (M) → M-24 paquete de cierre (M). Antes de M-18: confirmar con el contador régimen, impoconsumo, ICA y saldos iniciales.

## Log
(log del ciclo #7 cuenta PUC → archive/cuenta-puc/STATE.md)
2026-10-25 | 8-maintain | M-27 cerrado (v1.8.0); ciclo → archive/cuenta-puc/ (01–04, 06, 07, STATE; 01–03 no estaban en git); 08 al día (2 notas abiertas de It. 3); chequeo mensual 2026-11-17; próximo ciclo por elegir (M-26 recomendado o M-18)
