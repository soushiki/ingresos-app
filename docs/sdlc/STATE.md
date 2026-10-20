# SDLC state

project: ingresos_app · Rappi (01c #6)
goal: Que cada papel de Rappi se reconozca y entre al libro con su valor de producto («Total sugerido a facturar») como venta por cobrar a Rappi (13452501, medio App), y que el abono semanal del banco la salde, en vez de entrar como venta sin número ni valor.
size: S      # la ruta contable ya existe (POR_COBRAR si medio == "Rappi"; bloque «rappi» del extracto la salda); falta reconocer el papel y leer su ID y total
exposed: no  # app Flask local en 127.0.0.1
regulated: no  # cuentas del PUC que ya usa la app; sin valores tributarios
next: 5-implement

## Stages
- [x] 0-triage       (confirmado por el usuario 2026-10-19)
- [~] 1-research       (S: insumo en 01c #6 y 08 #6)
- [x] 2-requirements   (aprobado por el usuario 2026-10-19)
- [~] 3-design         (S)
- [x] 4-plan
- [ ] 5-implement      (T1–T4 hechos; FIX-1, FIX-2 de 6-test)
- [ ] 6-test           (1.ª pasada: falla, ver 06)
- [ ] 7-release
- [ ] 8-maintain

(Mark skipped stages `- [~]`.)

## Ciclos anteriores
- Documento soporte, precisión OCR v1.1.0, recibos omitidos v1.2.0, cierre de caja v1.3.0 + v1.3.1 (M-17) → `archive/<ciclo>/`.
- Siguen en su sitio: `01b`, `01c` (insumo de #5/#8), `01d`, `01e` (ignorado), `08-maintenance.md`, `adr/`.

## Punto de partida (de 08 #6 y del código)
- Modelo del usuario: Rappi cobra al cliente y paga al restaurante solo el producto, en liquidación semanal por banco; su comisión son débitos semanales aparte (gasto, no descuento de la venta).
- 19 papeles de Rappi en sept. entran como venta sin número ni valor (p. ej. 17-09, ID 1000000003, $30.000). Manual: 13452501 = [01f]; app: 0.
- `asientos.py` ya manda medio «Rappi» → 13452501 y el bloque «rappi» del extracto → débito banco / crédito 13452501. `campos.py` ya tiene la palabra «rappi».

## Wrong-road check
Lo más barato: anotar a mano el valor de los ≈ 19 papeles/mes en ④ con medio Rappi. Sirve, pero es trabajo fijo cada mes y el papel tiene un formato propio fácil de reconocer; el arreglo es S.

## Log
<!-- YYYY-MM-DD | stage | one-line result -->
2026-10-19 | 0-triage | Ciclo nuevo «Rappi» (01c #6), tamaño S, exposed no, regulated no; ciclo cierre de caja archivado (STATE + 07 v1.3.1). Preguntas: (1) valor = «Total sugerido a facturar» [def.]; (2) número = ID de Rappi, sin comanda [def.]; (3) rige al recalcular sept., con respaldo [def.]
2026-10-19 | 0-triage | Confirmado por el usuario: meta y tamaño S; (1) valor = «Total sugerido a facturar»; (2) número = ID de Rappi, sin comanda; (3) rige al recalcular sept., con respaldo → 2-requirements
2026-10-19 | 2-requirements | Borrador 02 (R1 reconocer papel + ID + total → 13452501; R2 ID repetido = 1 venta; R3 recalcular sept. con respaldo). Esperando aprobación
2026-10-19 | 2-requirements | Aprobado por el usuario (R1–R3) → 4-plan
2026-10-19 | 4-plan | 04-plan: 1 iteración ≈ 4 h — T1 leer papel Rappi (ID + total sugerido), T2 ID fuera de numeración + duplicado, T3 respaldo v1.4.0, T4 medir sept. → 5-implement
2026-10-19 | 5-implement | run: T1–T4 commiteados; sept. 13452501 = [01f] (antes 0) vs manual ≈ [01f] — faltan papeles de 17 días, no lectura; 11-sep 28150502 −[01f] sin explicar → 6-test
2026-10-19 | 6-test | FALLA: suites verdes, pero en leer_hoja el papel Rappi se re-parsea como venta (sin ID ni valor) → FIX-1; validar lo marca dudoso (hora/mesa) → FIX-2 → 5-implement
