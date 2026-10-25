# SDLC state

project: ingresos_app · Cuenta PUC por origen e ítem (M-27)
goal: la app decide la cuenta PUC de cada papel por su origen (comanda, cierre, gasto, extracto) y por el contenido de cada ítem (palabras, proveedor), repartiendo una factura con ítems de varias cuentas, aprendiendo de lo ya digitado en el Excel manual (cuadro `data/cuadro_clasificacion_puc.*`) y con el PUC como referencia (`puc.py`); lo que no se pueda decidir va a la cuenta puente y a revisión
size: M  # cambia el clasificador (una cuenta por papel → por ítem), reglas por origen, mapa a subcuentas PUC, recálculo de días guardados; evidencia ya existe (cuadro + inconsistencias)
exposed: no  # app Flask local en 127.0.0.1
regulated: yes  # la cuenta PUC va a los libros y a la renta; las 8 decisiones de «Qué decidir» son del contador
next: 5-implement
current task: T5c (re-medir, gate N1)

## Stages
- [x] 0-triage
- [x] 1-research  (ligera → 01-research.md)
- [x] 2-requirements
- [x] 3-design
- [x] 4-plan  (+ plan B ADR-023: T5a–T5c)
- [ ] 5-implement
- [ ] 6-test
- [ ] 7-release
- [~] 8-maintain

## Ciclos anteriores
- Documento soporte, precisión OCR v1.1.0, recibos omitidos v1.2.0, cierre de caja v1.3.0 + v1.3.1, Rappi v1.4.0, medio de pago v1.5.0, extracto bancario v1.6.0, Indra OCR v1.7.0 → `archive/<ciclo>/`.
- Siguen en su sitio: `01b`, `01c`, `01d`, `01e`, `01f`, `01g` (ignorados), `08-maintenance.md`, `adr/`.

## Pendientes
- Usuario: smoke de v1.6.0 (`archive/extracto/06-test-report.md`), avisar al contador del recálculo de sept. 1–23 y de las cuentas «por confirmar»; borrar la rama local `respaldo/antes-limpieza-v1.6.0` cuando ya no haga falta.
- Usuario: re-subir fotos Rappi de sept. (runbook en `archive/rappi/07-release.md`), actualizar los PC a v1.6.0, smoke de v1.3.x y v1.5.0 (pasos 1–3 en `archive/medio-de-pago/07-release.md`).
- Nuevo (2026-10-20): el POS es Ascomp; pasa a Vendty el mes que viene (≈ nov. 2026, aún no instalado), así que todo lo de hoy es Ascomp y M-25 sigue igual. Antes del cambio: preguntar a Ascomp (ascompos@hotmail.com, 3108094441, WhatsApp +57 320 4451364; tiene login en nube.ascomp-pos.com) si se pueden exportar las ventas pasadas a Excel/CSV; su web no documenta informes ni formato del recibo. Cuando arranque: fecha exacta, una foto de un recibo Vendty y pedir a Vendty la documentación de su «Api de integración» (sí existe, está en su web) y si el plan la incluye; con API o export Excel/CSV, posible ciclo «importar ventas Vendty» (S–M) en vez de OCR para los días nuevos. Abecé DIAN (feb. 2025): el tiquete POS es documento equivalente que la DIAN valida; persona natural no responsable de IVA/INC no está obligada salvo > 3.500 UVT → preguntar al contador por qué se pasó a POS electrónico (afecta M-18).
- Candidatos a ciclo: **M-26 recuperar número con Indra (S–M)** — usar los números que Indra ve en el recorte cuando qwen no da el número (omitidos 5/103 → ≤ 2). Marcador de renta (`docs/marcador-renta.html`) M-18 perfil fiscal (S) → M-19 NIT por tercero (S–M) → M-20 soporte por gasto + efectivo 771-5 (S) → M-21 impoconsumo bimestral (S) → M-22 pestaña Marcador (M) → M-23 cruce con facturas DIAN (M) → M-24 paquete de cierre (M). Antes de M-18: confirmar con el contador régimen, impoconsumo, ICA y saldos iniciales.

## Log
(log del ciclo #6 Indra OCR → archive/indra-ocr/STATE.md)
2026-10-24 | 8-maintain | M-25 cerrado (v1.7.0); ciclo → archive/indra-ocr/ (01–04, 06, 07, STATE; 01–03 no estaban en git); 08 al día; M-26 candidato; chequeo mensual 2026-11-17; falta elegir el próximo ciclo (M-26 recomendado o M-18)
2026-10-24 | 8-maintain | pedido del usuario (fuera de ciclo): export con «BALANCE x CTA <MES>» (fórmulas por fila, saldo inicial del mes anterior), códigos revisados contra el PUC (puc_cuentas.json, aviso si no existe), extracto lee todas las hojas con sus columnas (sept.: Hoja 1 1–23 + MOVIMIENTOS 1–30 → 643 líneas, claves de Hoja 1 iguales; reabre R1 del ciclo extracto); revisión del manual → data/revision_manual_septiembre_2026.xlsx
2026-10-24 | 8-maintain | M-27 anotado: cuenta PUC por origen + ítem (pedido del usuario); cuadro de clasificación con 1.537 filas del manual → data/cuadro_clasificacion_puc.{xlsx,pdf}; informe del manual: sección PUC sin sugerencias de subcuenta, remite al cuadro
2026-10-24 | 0-triage | M-27 borrador: meta (cuenta PUC por origen + ítem, aprende del manual, PUC de referencia), M, exposed no, regulated yes (decisiones del contador); alternativa barata: solo ampliar LEXICO (25 palabras) y arreglar 5 choques, una cuenta por papel; informe `data/inconsistencias_clasificacion_puc.pdf` → esperando confirmación
2026-10-25 | 0-triage | confirmado por el usuario: meta y tamaño M; factura con ítems de varias cuentas se reparte por ítem; los 8 puntos del contador van por regla de mayoría del manual, marcados «por confirmar» → next 1-research (ligera)
2026-10-25 | 2-requirements | borrador 02-requirements.md: R1–R8 Must, R9–R10 Should, N1 ≥ 85 % por ítem sept–oct; hallazgo: factura y gasto no sacan ítems hoy (R2); Q1–Q3 abiertas → esperando aprobación
2026-10-25 | 1-research | 01-research.md: capas sin deps nuevas (origen → enseñado → léxico → léxico minado del cuadro → vecino difflib → puente), sklearn plan B; validar por mes; hoy 1 cuenta por papel y 1 débito; PUC auxiliares 8 díg. bajo subcuenta oficial; 7 riesgos (ítems con valor fuera de venta, suma ≠ total, no pisar lo manual)
2026-10-25 | 2-requirements | aprobado por el usuario con defaults (Q1 N1 85 % por ítem, Q2 diferencia → puente + revisión, Q3 botón «Reclasificar mes» con vista previa) → next 3-design
2026-10-25 | 3-design | borrador 03-design.md + ADR-019 (fila DATOS OCR por papel×cuenta), 020 (motor por capas + modelo_manual.json minado), 021 (reclasificar plan+huella → aplicar, 1 escritura), 022 (por_confirmar.json + puc_valida); hallazgo: el libro no guarda items (sí texto); spike de ítems de factura pendiente → esperando aprobación
2026-10-25 | 3-design | aprobado por el usuario (ADR-019…022 aceptados) → next 4-plan
2026-10-25 | 4-plan | 04-plan.md: 3 iteraciones, 12 tasks (5 S + 7 M) ≈ 13 h; It.1 mide primero (spike ítems, minado, motor, informe N1 = gate plan B) → next 5-implement
2026-10-25 | 5-implement | T1 spike ítems de factura: sept. 96 facturas, 39 (41 %) con ítems con valor, 3 (3 %) cuadran ±1 % → factura = ítem único + proveedor salvo las que cuadran; T6 debe leer mejor el total
2026-10-25 | 5-implement | T2 minar_manual.py → modelo_manual.json (74 palabras, 35 proveedores, 204 vecinos, jun–oct); probar_minado 16 checks OK; «pan» descartado como token de persona
2026-10-25 | 5-implement | T3 Motor por capas en clasificar.py (origen→enseñado→léxico→minado/proveedor→vecino→puente); probar_motor 18 checks, 1.000 ítems 0,16 s; 35 % a puente en ítems sintéticos (T5 da la cifra real)
2026-10-25 | 5-implement | T4 por_confirmar.json (alias, 8 decisiones, origen) + puc_valida al final del motor; 1er intento Sonnet falló revisión (capas minadas solo avisaban, sin alias) → reintento Opus OK; fitness ADR-022 en probar_motor (35 checks); 51104002 a puente hasta decisión 7
2026-10-25 | 5-implement | T5 medir_clasificacion (jun–ago → sept–oct, 317 ítems de gasto): 57,4 % por ítem (con alias); decide 61 % y acierta 94 % de lo que decide; 124 a puente («sin palabras conocidas»); 5 cuentas ≥ 10 ítems < 60 % → GATE N1 FALLA, parado; informe logs/medir_clasificacion_2026-10-25.txt
2026-10-25 | 5-implement | ADR-023 plan B (pedido del usuario): ampliar cobertura — proveedores jun–oct (personas a terceros_cuentas.json local), bigramas/FRASES, barrido umbral vecino, cruce «Recibo N» con el libro; gate N1 igual (jun–ago → sept–oct) + walk-forward; tasks T5a–T5c
2026-10-25 | 5-implement | T5a (run parado por el usuario): minar_manual.py con bigramas (94), modelo jun–oct, terceros persona → terceros_cuentas.json (gitignored); probar_minado TODO OK; diff dentro de los files de T5a; SIN COMMIT. Suite: 16/26 OK hasta probar_motores; probar_motores_falso.py se colgó 2 h (0 CPU, matado; no es de T5a → anotar en 08); faltan probar_parser…probar_variantes (10). Reanudar: correr esos 10 + motores_falso, commit T5a, /sdlc run → T5b
2026-10-25 | 5-implement | T5a reanudado: suite completa verde (25 tests; probar_motores_falso es el trabajador falso, no test → M-28 cerrado); commit T5a
2026-10-25 | 5-implement | T5b capa proveedor lee terceros_cuentas.json (o .example), bigramas minados, FRASES «pago de compras» → 14050501, capa «confirmar» (domiciliario 28150501, por_confirmar motor:true); probar_motor +8 checks; suite 24/24 verde; «día laborado» sin frase (sin cifra de mayoría)
