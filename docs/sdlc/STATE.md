# SDLC state

project: ingresos_app · Recuperar número con Indra (M-26)
goal: cuando qwen no da el número de un recibo Ascomp, la app lo recupera de los números que Indra lee en el recorte (el que cae en el rango que da el nombre de la foto, R5), lo marca «número recuperado» para revisar, y baja los omitidos de 5/103 a ≤ 2/103 sin números equivocados
size: S  # una regla nueva en la validación (R5 + lectura de Indra que ya existe), tests y medir en la referencia de 103; sin deps ni pantallas nuevas
exposed: no  # app Flask local en 127.0.0.1
regulated: no  # el número de recibo no es un valor fiscal; no cambia cuentas ni montos
next: 5-implement
current task: T2 (paso 4 de leer_hoja con los números de Indra)

## Stages
- [x] 0-triage
- [~] 1-research  (salta, S)
- [x] 2-requirements  (5 líneas)
- [~] 3-design  (salta, S)
- [x] 4-plan
- [ ] 5-implement
- [ ] 6-test
- [ ] 7-release

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
2026-10-25 | 0-triage | M-26 borrador: meta (número desde Indra + R5, marcado «recuperado», omitidos ≤ 2/103, 0 números malos), S, exposed no, regulated no; alternativa barata: seguir anotando a mano los «Falta N» (≈ 5 por 100 recibos); ojo: Vendty ≈ nov. puede volver innecesario el OCR de recibos nuevos → esperando confirmación
2026-10-25 | 0-triage | confirmado por el usuario: meta y tamaño S; defaults: número recuperado cuenta y va a ④ marcado «número recuperado»; hecho = ≤ 2/103 omitidos con 0 números malos; solo motores locales, sin deps nuevas → next 2-requirements
2026-10-25 | 2-requirements | borrador S (5 líneas) en 02-requirements.md: R1 números de Indra cuentan en el paso R5 de cercanía (candidato único, «dudoso» con motivo), R2 tests + medir ≤ 2/103 con 0 malos → esperando aprobación
2026-10-25 | 2-requirements | aprobado por el usuario tal cual (motivo «Número recuperado por el segundo lector…») → next 4-plan
2026-10-25 | 4-plan | 04-plan.md: 1 iteración, T1 (S) lectura.digitos en leer_recibo, T2 (M) paso 4 con Indra + RECUPERADO + 5 tests, T3 (S) contadores recuperados/recuperados_con_error + medición 103 → next 5-implement
2026-10-25 | 5-implement | T1 hecho (Sonnet): leer_recibo guarda lectura.digitos (unión ordenada de leer_digitos); 3 checks en probar_relectura.py; relectura/motores_falso/contable/faltantes verdes → next T2
