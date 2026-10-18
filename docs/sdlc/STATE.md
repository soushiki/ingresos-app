# SDLC state

project: ingresos_app · documento soporte
goal: Desde los gastos que la app ya registra, preparar los documentos soporte de compras a proveedores no obligados a facturar, acumulados por proveedor y semana, listos para que contabilidad los revise y los transmita a la DIAN.
size: M      # una función nueva de varios días; requisitos DIAN (Res. 000167/2021 y 000165/2023) que hay que confirmar antes de diseñar
exposed: no  # app Flask local en 127.0.0.1, sin acceso desde la red
regulated: yes  # documento tributario: consecutivo, campos y plazos los fija la DIAN; la app prepara, no transmite
next: 8-maintain   # v1.0.1 publicada (tag en 78599fb, rama pusheada); M-4 en la rama y versiones fijas (sin commit), sin publicar; espera al usuario: M-5 (datos), #9 (contabilidad); luego #2/#4 (ciclo S, desde 0-triage)

## Stages
- [x] 0-triage
- [x] 1-research   (light: requisitos del documento soporte y cómo lo emite Vendty o la solución gratuita DIAN)
- [x] 2-requirements   (gate: user approval)
- [x] 3-design         (gate: user approval)
- [x] 4-plan
- [x] 5-implement      current task: —
- [x] 6-test           (iter. 1–4 pasan; smokes pendientes, usuario)
- [x] 7-release      (v1.0.0, 2026-10-17)
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
2026-10-17 | 6-test | Re-test iter. 2: pasa; FIX-7…10 cerrados con sus checks, suite verde, datos reales sin años raros (17 grupos 2026, 5 elegir, 5 avisos); 1 menor de Host con «@» (no explotable) → 06-test-report.md
2026-10-17 | 5-implement | T14: POST /api/soporte/compra (valida fecha, proveedor, descripción ≤200, valor 1–10^10, medio) guarda factura origen «manual» en el día y lo recalcula; tarjeta «Compra manual» en ③ (verificada a 375 px, sin guardar en datos reales); 15 checks; suites verdes
2026-10-17 | 5-implement | T15: transmitido (CUDS 96 hex opcional), anular (motivo; ADR-003), bloqueos() en guardar/borrar día (409); vendedor fijo al generar (migración 2); tarjeta «Documentos numerados» en ③ verificada en copia y 375 px; 37 checks; suites verdes
2026-10-17 | 5-implement | T16: nota_ajuste (solo sobre DS transmitido; concepto, líneas ≠0, no deja el DS negativo), rango_na configurable (default NA 1–10000, sin reutilizar al cambiarlo), migración 3 (concepto), hoja NA + «Ajusta a» en RESUMEN, POST /api/soporte/<id>/ajuste; 40 checks; suites verdes. Falta botón en ③ (contable.html fuera de la tarea)
2026-10-17 | 5-implement | T17: 3 checks N4 (50 DS en 0,07 s, Excel soporte 0,15 s, Excel del libro de sept. real en 0,50 s; límites 2/2/5 s); suites verdes. Iteración 3 completa → 6-test
2026-10-17 | 6-test | Iter. 3 no pasa: suite verde y R4/R7/R8/N1/N2/N4 con checks, pero falta el botón de nota de ajuste en ③ (FIX-11) y hay inyección de fórmulas en los Excel (FIX-12) → 06-test-report.md
2026-10-17 | 5-implement | FIX-11: botón «Nota de ajuste» en DS transmitidos (concepto + líneas ±, total en vivo) y «Ajusta a CTG-N» en la tabla; demo en copia: CTG-1 → −20.000 → NA-1, su ⬇ trae hoja NA-1; 375 px sin desborde; suites verdes
2026-10-17 | 5-implement | FIX-12: texto que empieza por = + - @ (o tab/CR) queda como texto con quotePrefix en soporte_excel (todo el libro) y exportar (DATOS OCR, MOVIMIENTOS salvo F/G, AVISOS); 4 checks; suites verdes → 6-test
2026-10-17 | 6-test | Re-test iter. 3: pasa; FIX-11 y FIX-12 cerrados, suite verde, sin defectos nuevos; smokes it. 1–3 pendientes (usuario) → it. 4
2026-10-17 | 5-implement | D1 propuesto: .json versionado con sha256 (no xlsx/CSV), sin fotos, import día a día (nuevo entra, distinto = conflicto a elegir, transmitido nunca), soporte.db solo en el PC del contador → 03-design §10, adr/004; gate pendiente
2026-10-17 | 5-implement | D1 aprobado por el usuario: ADR-004 aceptado; sigue T18
2026-10-17 | 5-implement | T18: exportar.crudo/huella (ADR-004: formato, version 1, sha256, solo documentos/banco/cierre/guardado), GET /api/contable/crudo (rango, 400/404, Host), botón «Datos crudos (.json)» en ②; 30 días reales ida y vuelta iguales; arreglado desborde de ② a 375 px (como #m3); 10 checks; suites verdes
2026-10-17 | 5-implement | T19: exportar.leer_crudo (JSON/formato/versión/sha256 rechazan todo; por día fecha, tipo, 0–10^10, textos ≤5.000, ≤2.000 docs, repetidos) + POST /api/contable/crudo (nuevos/iguales/conflictos/bloqueados R7/inválidos R10, reemplazar marcados, una escritura) + «⬆ Importar datos crudos» en ②; 30 días reales → mismas filas y semanas; 14 checks; suites verdes
2026-10-17 | 5-implement | T20: SIN_OCR=1 (no busca a Ollama, foto → error claro; PDF con texto sí) y /api/estado.sin_ocr (también con Ollama apagado); ① cambia «Leer» por «⬆ Importar datos» + aviso; arreglado desborde de ① a 375 px; 8 checks (subproceso con Ollama apagado → importa → CTG-1); suites verdes
2026-10-17 | 5-implement | T21: LEEME-contador.md (Python con PATH, copiar sin datos/, pip, .env SIN_OCR=1, iniciar.bat, trabajo semanal, copia de soporte.db, tabla de fallas); probado en copia limpia (git archive + venv nuevo): arranca sin OCR, importa 30 días reales, 17 semanas en ③. Iteración 4 completa → 6-test
2026-10-17 | 6-test | Iter. 4 no pasa: suite verde y done-when de T18–T21 con checks, pero un día con faltante (número negativo) se rechaza al importar (FIX-13) y el tope de texto 5.000 está justo + RecursionError → 500 (FIX-14) → 06-test-report.md
2026-10-17 | 5-implement | FIX-13: _malo acepta |v| ≤ 10^10 (faltante_impreso negativo); cierre con faltante va y vuelve igual por crudo → leer_crudo → POST; caso -5 → 10^11; ADR-004 anota el tope; suites verdes
2026-10-17 | 5-implement | FIX-14: MAX_TEXTO 5.000 → 20.000 (texto de 6.000 entra); RecursionError de json.loads → CrudoInvalido (anidado 100.000 niveles → 400 sin escribir); ADR-004 anotado; 2 checks; suites verdes → 6-test
2026-10-17 | 6-test | Re-test iter. 4: pasa; FIX-13/14 cerrados, suite verde, 30 días reales + día con faltante van y vuelven; sin defectos nuevos → 7-release (smokes it. 1–4 pendientes)
2026-10-17 | 7-release | v1.0.0 preparada: runbook 07-release.md, CHANGELOG.md, VERSION; pre-flight verde (8/8, sin secretos, debug off, 127.0.0.1). Merge/tag/push esperan smokes y ok del usuario
2026-10-17 | 7-release | v1.0.0 publicada: smokes it. 1–4 ok (usuario); main = 3c7e316, tag v1.0.0, push. 01b/01c fuera del repo público (cifras reales)
2026-10-17 | 8-maintain | 08-maintenance.md: 3 bugs XS (M-1 valor negativo, M-2 id repetido, M-3 Host «@»), 5 ítems de 01c, extracto (M), debt linter; pip-audit sin instalar → chequeo 2026-11-17
2026-10-17 | 8-maintain | M-1 (valor negativo fuera del cierre), M-2 (id repetido en el día) y M-3 («@» en Host) cerrados test-first; 3 checks nuevos; suites verdes, libro real va y vuelve. Commit v1.0.1 (sin push)
2026-10-17 | 8-maintain | 01c #9 investigado: sin duplicados. La app sigue al POS y el manual al banco; al manual le falta el efectivo del 27-09 y el crédito/puente del 30-09. M-4 nuevo (comanda 85767 del 20-09 cayó en el 27-09)
2026-10-17 | 8-maintain | M-4: aviso de comanda fuera de secuencia (salto_comanda 30); 2 checks; suites verdes. Datos reales: 6 días con aviso (85767, 85726 de otro día; 5 números mal leídos) → M-5. Sin commit
2026-10-17 | 8-maintain | Revisión: M-4 ya commiteado (ff5ca34). Nada abierto se puede hacer sin el usuario: push/tag v1.0.1, M-5 (datos), #9 (contabilidad), #2/#4 (nuevo ciclo); chequeo mensual 2026-11-17
2026-10-17 | 8-maintain | v1.0.1 publicada: tag anotado en 78599fb (el CHANGELOG deja M-4 sin publicar), push de feat/documento-soporte (hasta ff5ca34) y del tag. main sin tocar
2026-10-17 | 8-maintain | pip-audit adelantado (venv aparte, 21 paquetes instalados): sin vulnerabilidades; falta fijar versiones en requirements.txt. Lo demás sigue esperando al usuario (M-5, #9, push de M-4)
2026-10-17 | 8-maintain | requirements.txt con `==` a las versiones auditadas (+werkzeug, jinja2); resuelve en Python 3.12/3.13/3.15 Windows; suites verdes. Sin commit. Lo demás espera al usuario (M-5, #9)
2026-10-17 | 8-maintain | Revisión: nada nuevo que se pueda hacer sin el usuario. Listo para commit: requirements.txt fijo (+ STATE). Esperan: M-5 (datos), #9 (contabilidad), push de M-4; chequeo mensual 2026-11-17
