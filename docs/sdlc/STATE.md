# SDLC state

project: ingresos_app · documento soporte
goal: Desde los gastos que la app ya registra, preparar los documentos soporte de compras a proveedores no obligados a facturar, acumulados por proveedor y semana, listos para que contabilidad los revise y los transmita a la DIAN.
size: M      # una función nueva de varios días; requisitos DIAN (Res. 000167/2021 y 000165/2023) que hay que confirmar antes de diseñar
exposed: no  # app Flask local en 127.0.0.1, sin acceso desde la red
regulated: yes  # documento tributario: consecutivo, campos y plazos los fija la DIAN; la app prepara, no transmite
next: 6-test   # re-test iter. 2 (FIX-7…10); luego iter. 3 desde T14; it. 4 (OCR separado) después; smoke en Excel pendiente (usuario)

## Stages
- [x] 0-triage
- [x] 1-research   (light: requisitos del documento soporte y cómo lo emite Vendty o la solución gratuita DIAN)
- [x] 2-requirements   (gate: user approval)
- [x] 3-design         (gate: user approval)
- [x] 4-plan
- [ ] 5-implement      current task: — (FIX-10 hecho; sigue T14 tras 6-test)
- [ ] 6-test           (iter. 1 pasa; iter. 2 no pasa: FIX-7…10; smokes pendientes)
- [ ] 7-release
- [~] 8-maintain

(Mark skipped stages `- [~]`.)

## Decisiones de triage (confirmadas 2026-10-16)
- Alternativa más barata: llenar a mano el modelo Excel de Actualícese (VA23) o usar la solución gratuita de la DIAN. La app se justifica porque ya tiene los gastos, terceros y valores: evita volver a digitar.
- Alcance propuesto: la app arma y numera los documentos (Excel por proveedor-semana + resumen); NO firma ni transmite a la DIAN.
- Proveedor «no obligado»: marca por tercero con su cédula/NIT y datos, guardada una vez y reutilizada.

## Insumos para requisitos (usuario, 2026-10-16)
- Emisión: solución gratuita DIAN (transcripción manual desde el Excel de la app).
- Numeración DIAN: prefijo CTG, rango 1–10000. Vigencia: se asume vigente hasta nuevo aviso (autorización a 2 años; sin fecha en la app).
- Nota de ajuste: la app también la prepara (con número propio, sin reutilizar el original). No transmite.
- Reporte contable manual corregido y analizado → `01b-reporte-contable.md` (cuadra; formato de columnas MOVIMIENTOS = referencia de exportación).
- App vs manual (sept.) → `01c-app-vs-manual.md`: app capta 64 % de ingresos, ~4 % de gastos, 10 % de compras; 9 cambios priorizados. Decidir en requisitos qué entra antes del documento soporte.
- Pedido del usuario: el Excel trae una hoja «DATOS OCR» (una fila por papel leído, con archivo de origen, estado y aviso) y MOVIMIENTOS se calcula desde ella con fórmulas, así lo mal leído o faltante se ve y se corrige a mano. Nota para diseño: preferir fórmulas (SUMIFS por día/medio/cuenta) a macros (.xlsm, bloqueadas por seguridad); openpyxl escribe fórmulas y Excel calcula al abrir.

## Log
<!-- YYYY-MM-DD | stage | one-line result -->
2026-10-16 | 0-triage | Tamaño M, exposed no, regulated yes; alcance: preparar, no transmitir. Confirmado por el usuario.
2026-10-16 | 1-research | Salida Excel propio + contador de numeración local; sin carga masiva DIAN confirmada; 7 riesgos → 01-research.md
2026-10-16 | 2-requirements | Aprobado: R1–R10 (R9 DATOS OCR y R10 cuenta puente van primero), semana lun–dom, nota de ajuste con contador aparte → 02-requirements.md
2026-10-16 | 3-design | Aprobado: fase A (DATOS OCR+puente) luego B (soporte en SQLite, numeración reservada); plazo configurable, default misma semana → 03-design.md, adr/001-003
2026-10-16 | 4-plan | 3 iteraciones, 17 tareas (≈19–20 h): A (R10, R9) → B de punta a punta → ciclo de vida → 04-plan.md
2026-10-16 | 5-implement | T1: tope de propina+domicilio al efectivo probado (check nuevo en probar_contable.py); suites verdes
2026-10-16 | 5-implement | T2: cuentas puente (venta sin medio, gasto sin cuenta) + pendientes; filas con `docs`; 5 checks nuevos. probar_pdf.py ya fallaba antes (cierre en papel)
2026-10-16 | 5-implement | T3: guarda de exportación; fila sin código → 0 en MOVIMIENTOS + hoja AVISOS; 2 checks nuevos
2026-10-16 | 5-implement | T4: spike ADR-002 confirmado; 30 días/408 asientos con fórmula = construir(); DATOS OCR pasa a 1 fila por papel y medio. Falta abrirlo en Excel
2026-10-16 | 5-implement | T5: hoja DATOS OCR (asientos.datos_ocr, primera hoja del export); 921 papeles reales → todos con fila (68 ventas ilegibles como «pendiente»); probar_datos_ocr.py 13 checks
2026-10-16 | 5-implement | T6: MOVIMIENTOS con fórmulas (SUMIFS/ref/MIN) hacia DATOS OCR; 8 checks nuevos; 30 días reales evaluados = construir(). Iteración 1 completa → 6-test
2026-10-16 | 6-test | Iter. 1 no pasa todavía: suites verdes (probar_pdf ya fallaba antes), la revisión da 4 defectos R9/R10 + 1 decisión + 1 DEBT → FIX-1…6 en 04-plan; smoke en Excel pendiente → 06-test-report.md
2026-10-16 | 5-implement | FIX-1: día con solo pendientes (facturas sin valor) se guarda; libro guarda `pendientes`; botón Confirmar ya no lo bloquea; 2 checks nuevos
2026-10-16 | 5-implement | FIX-2: filas «dato» (factura, extracto, Rappi) = IF(estado="ok"; valor; 0); evaluador del test con IF y «=»; 2 checks nuevos
2026-10-16 | 5-implement | FIX-3: caja menor agrupa por cuenta efectiva (sin cuenta = puente_gasto) → 1 fila, 1 SUMIFS; 2 checks nuevos; débito = crédito en Excel
2026-10-16 | 5-implement | FIX-4: efectivo 0 con propina/domicilio en efectivo → aviso con las cifras (sin filas de caja; la fila de DATOS OCR queda); 1 check nuevo
2026-10-17 | 5-implement | FIX-5: test desactualizado (la venta sola ya da 5 filas); el check ahora exige filas con cierre = filas sin cierre; todas las suites verdes
2026-10-17 | 5-implement | FIX-6: el usuario eligió recalcular + avisar; AVISOS lista los días cuyo débito/crédito cambió desde que se confirmaron; 2 checks nuevos; suites verdes
2026-10-17 | 6-test | Re-test iter. 1: pasa; suite completa verde (probar_pdf incluido), revisión de FIX-1…6 sin defectos nuevos; smoke en Excel pendiente (usuario); DEBT-1 abierto → 06-test-report.md
2026-10-17 | 5-implement | DEBT-1: construir() arma las filas desde DATOS OCR (una sola clasificación); salida idéntica en 60 días-variante reales; 2 checks nuevos; suites verdes
2026-10-17 | 5-implement | T7: soporte_db.py (esquema 03 §4, user_version, semilla DS CTG 1–10000, reservar_numero en BEGIN IMMEDIATE); 16 checks en probar_documento_soporte.py; suites verdes
2026-10-17 | 5-implement | T8: proveedores.py (guardar con validación DIAN de tipo/número/DV, alias normalizado, asociar sin robar, resolver, es_encabezado); 18 checks; suites verdes
2026-10-17 | 5-implement | T9: soporte.py (semanas por proveedor y semana ISO, fecha_limite con festivos, estados en_plazo/vence_pronto/vencida; terceros sin registrar aparte); 18 checks; suites verdes
2026-10-17 | 5-implement | T10: soporte.generar en un BEGIN IMMEDIATE (todo o nada); rechaza proveedor sin registrar, compra ya documentada y vencida sin confirmar; linea con copia fija y origen; 13 checks; suites verdes. fecha_limite no se guarda en BD (T11 la toma de los grupos)
2026-10-17 | 5-implement | T11: soporte_excel.libro (RESUMEN + una hoja por documento con campos art. 4); Sonnet no escribió los checks → reintento Opus añadió 4; suites verdes. Ojo T12: docs leídos de BD traen fecha_limite None (recalcular con soporte.fecha_limite)
2026-10-17 | 5-implement | T12: rutas soporte/semanas, generar, excel y proveedores; before_request 403 a POST con Host/Origin no locales (toda la app); config de contable.json; excel recalcula fecha_limite; 17 checks; suites verdes. Abierto: semanas lista también las ya documentadas (T13)
2026-10-17 | 5-implement | T13: pestaña ③ Documento soporte (semanas con estado, registrar proveedor, generar, Excel); semanas trae `documentado` y se ocultan; verificada en preview escritorio y 375×812 (arreglo: #m3 se desbordaba a 770 px); suites verdes
2026-10-17 | 5-implement | Hallazgos del preview con datos reales (para 6-test): semanas agrupadas por la fecha OCR de la factura → semanas 2018-W39/2024-W52 «vencidas hace 2100 d» (años mal leídos); «Sin Texto» aparece como tercero (es_encabezado no lo filtra en semanas)
2026-10-17 | 5-implement | Iteración 2 completa (T7–T13) → 6-test
2026-10-17 | 4-plan | Pedido del usuario: separar la lectura OCR (el PC del contador no la corre) → it. 4 en 04-plan (D1 + T18–T21), después de la it. 3
2026-10-17 | 6-test | Iter. 2 no pasa: suites verdes y 85 checks, pero 3 defectos de Must (semana documentada + compra nueva bloqueada, «Sin Texto» agrupado, 5/17 fechas OCR con año mal) + Host sin revisar en GET → FIX-7…10 → 06-test-report.md
2026-10-17 | 6-test | FIX-9 decidido: fecha OCR a >7 días del día → usa la del día y avisa con las dos (tolerancia configurable)
2026-10-17 | 5-implement | FIX-7: compras ya documentadas forman su grupo con `documentado`; lo nuevo de la semana se numera aparte (CTG-2 solo con b); generar/ruta prefieren lo no documentado; 8 checks; suites verdes
2026-10-17 | 5-implement | FIX-8: tercero rótulo («Sin Texto», vacío) → un grupo «elegir proveedor» por compra, sin botón Registrar; 2 checks; datos reales: 5 grupos así, 12 Registrar legítimos; suites verdes
2026-10-17 | 5-implement | FIX-9: fecha del papel a >tolerancia_fecha_dias (7) del día → fecha del día + aviso con las dos en el grupo y la pestaña; 5 checks; datos reales: 5 avisos, ninguna semana fuera de 2026; suites verdes
2026-10-17 | 5-implement | FIX-10: Host local revisado en todo método (GET con Host ajeno → 403 en proveedores, semanas, excel); acepta [::1]; 6 checks; suites verdes → 6-test
