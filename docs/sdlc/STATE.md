# SDLC state

project: ingresos_app · extracto bancario (01c #5)
goal: Leer el extracto del banco (Excel/CSV descargado) y que cada línea quede clasificada (nómina, arriendo, servicios, 4x1000, rendimientos, abonos Rappi, proveedores, transferencias de venta) y genere su asiento en el libro y el Excel; lo dudoso queda para que el usuario elija la cuenta.
size: M      # importador nuevo + reglas de clasificación + asientos con cuentas PUC nuevas + pantalla de revisión; días, no horas
exposed: no  # app Flask local en 127.0.0.1
regulated: yes  # asientos de gasto/impuesto con cuentas PUC y tasa 4x1000: confirmar con contabilidad antes de diseñar
next: 5-implement
current task: T9 (incluye sin_asiento en asientos.py + facturas= en app.py)

## Stages
- [x] 0-triage       (confirmado por el usuario 2026-10-20: Excel/CSV sin OCR; v1 = clasificar + asientos; regulado)
- [x] 1-research     (light: muestra real Bancolombia + hoja MOVIMIENTOS etiquetada; riesgo doble conteo con casillas banco)
- [x] 2-requirements (aprobado 2026-10-20: R1–R9; casillas banco se llenan del extracto; cuentas del manual en JSON «por confirmar»; tarjetas por neto)
- [x] 3-design       (aprobado 2026-10-20: ADR-012..015, incluido 015 salida↔factura)
- [x] 4-plan         (13 tareas en 3 iteraciones ≈15–16 h)
- [ ] 5-implement
- [ ] 6-test
- [ ] 7-release
- [ ] 8-maintain

## Ciclos anteriores
- Documento soporte, precisión OCR v1.1.0, recibos omitidos v1.2.0, cierre de caja v1.3.0 + v1.3.1, Rappi v1.4.0, medio de pago v1.5.0 → `archive/<ciclo>/`.
- Siguen en su sitio: `01b`, `01c` (insumo de #5/#8), `01d`, `01e`, `01f` (ignorados), `08-maintenance.md`, `adr/`.

## Pendientes
- (hecho 2026-10-19) push de main + tag v1.4.0.
- (hecho 2026-10-20) push de main + tag v1.5.0.
- Usuario: re-subir fotos Rappi de sept. (runbook en `archive/rappi/07-release.md`), actualizar los PC a v1.5.0, smoke de v1.3.x y v1.5.0 (pasos 1–3 en `archive/medio-de-pago/07-release.md`).
- Candidatos a ciclo: M-16 lector por línea (M).

## Log
<!-- YYYY-MM-DD | stage | one-line result -->
(log del ciclo #8 → archive/medio-de-pago/STATE.md)
2026-10-19 | 8-maintain | revisión: sin ítems nuevos, 08 al día; chequeo mensual 2026-11-17; falta elegir el próximo ciclo (#8 S recomendado)
2026-10-20 | 7-release | push main + tag v1.5.0 a origin (550907b..c7da075)
2026-10-20 | 8-maintain | #8 cerrado (v1.5.0); ciclo → archive/medio-de-pago/ (02, 04, 06, 07, STATE); 08 al día; sin ítems nuevos; chequeo mensual 2026-11-17; falta elegir el próximo ciclo (#5 o M-16)
2026-10-20 | 8-maintain | sin ítems nuevos; usuario elige próximo ciclo: #5 extracto bancario (M) → next 0-triage
2026-10-20 | 0-triage | #5 extracto bancario: Excel/CSV (sin OCR), v1 clasificar + asientos, M, regulated yes → next 1-research
2026-10-20 | 1-research | 01-research.md: formato real (4 col, Valor con signo), concepto por reglas ancladas, cuenta de salidas = usuario + memoria por tercero; riesgo doble conteo; preguntas a contabilidad → next 2-requirements
2026-10-20 | 2-requirements | 02-requirements.md aprobado: 9 historias (6 Must), P1 llenar casillas, P2 cuentas JSON por confirmar, P3 tarjeta neto → next 3-design
2026-10-20 | 3-design | 03-design.md + ADR-012 (extracto en el día, casillas derivadas), 013 (reglas JSON), 014 (memoria por tercero), 015 (salida↔factura); gate pendiente
2026-10-20 | 3-design | aprobado por el usuario (incl. ADR-015) → next 4-plan
2026-10-20 | 4-plan | 04-plan.md: 13 tareas (9 M + 4 S) en 3 iteraciones ≈15–16 h; it.1 importar + asientos automáticos → next 5-implement T1
2026-10-20 | 5-implement | T1 reglas extracto (JSON 14 reglas, clasificar) 511/513 = 99,6 % vs MOVIMIENTOS, 2 excepciones aceptadas; 24–30 sept sin oráculo → T2
2026-10-20 | 5-implement | T2 leer_xlsx (ExtractoInvalido, topes 5 MB/5 000 filas, ocurrencia+clave sha1) real 513 líneas, suma = Valor; 20 suites verdes → T3 (opus)
2026-10-20 | 5-implement | T3 bloque 5 «Extracto» en construir (GMF, rendimientos, cuenta Rappi, revisar → puente + pendiente) cuadra en libro y Excel; 20 suites verdes → T4
2026-10-20 | 5-implement | T4 POST /api/contable/extracto (todo o nada, mezcla por clave, memoria tmp+replace) +14 checks, real 513 < 3 s; 20 suites verdes; hallazgo: _dia borra `extracto` al editar un día → añadido a T6 → T5
2026-10-20 | 5-implement | T5 pestaña ⑤ Extracto: subir septiembre «513 nuevas · 94 por revisar», re-subir no duplica, error claro, 375/768 px ok; hallazgo arreglado: export Excel no pasaba extracto= (app.py); datos reales restaurados; 20 suites verdes; iteración 1 completa → next 6-test
2026-10-20 | 6-test | it.1: 20/20 suites verdes; R1, R2, R6, R7, R8 cubiertos; review: FIX-1 clasificar duplica avisos al reclasificar (añadido al inicio de la it.2); smoke del usuario pendiente → next 5-implement FIX-1
2026-10-20 | 5-implement | FIX-1 clasificar idempotente (recalcula sus 2 avisos, conserva otros) +2 checks; 20 suites verdes → T6 (opus)
2026-10-20 | 5-implement | T6 casillas efectivas (vacía = extracto, digitada manda + aviso dif) y `extracto` conservado en todos los recálculos de app.py; +13 checks; 20 suites verdes; real simulado 23 días cuadran → T7
2026-10-20 | 5-implement | T7 memoria por tercero (tercero_de + prefijos_tercero; solo líneas a revisar; sin_tercero nunca se recuerda; origen «recordada») +9 checks; 20 suites verdes → T8
2026-10-20 | 5-implement | T8 enlace salida↔factura en clasificar (1 candidata → factura + confirmar; 2+ → revisar «¿cuál factura?» sin_asiento; ±3 días) +11 checks incl. fitness ADR-015; 20 suites verdes; abierto: asientos.py aún pone puente a sin_asiento y app.py no pasa facturas → T9
2026-10-20 | 5-implement | usuario: el abierto de T8 (sin_asiento en asientos.py, facturas= en app.py) entra en T9
