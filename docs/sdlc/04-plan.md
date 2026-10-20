# 4 · Plan — Rappi (01c #6) · tamaño S

## Summary
Una iteración (≈ 4 h): T1 reconocer el papel de Rappi y leer ID + «Total sugerido a facturar» (R1), T2 que el ID largo no rompa
la numeración de comandas y que un ID repetido cuente una vez (R1/R2), T3 respaldo antes de recalcular (R3), T4 medir septiembre
(aceptación). La ruta contable ya existe: medio «Rappi» → débito 13452501, tercero Rappi, medio App (`asientos.py:215`); el bloque
«rappi» del extracto la salda (`asientos.py:315`) y no se toca.

Formato real del papel (OCR de `2/comandas/85319-318-rappi.jpg#1`, hoy entra como venta sin número ni valor):
`Rappi` · nombre · `ID 1000000001` · `Restaurante: …` · `Plataforma: WEB` · `Fecha orden: 2026-09-02 21:00` · ítems ·
`Subtotal $25.000` · `Total sugerido a facturar $25.000` · (se repite nombre + ID al pie, «VERIFICA LOS PRODUCTOS»).

## Iteración 1 — los papeles de Rappi entran a 13452501 con su ID y su valor
- [x] T1 (M) Leer el papel de Rappi — R1, aceptación (fila 17-09) — model: Sonnet
  — `detectar_tipo`: nuevo tipo «rappi» si el texto trae «rappi» y («sugerido a facturar» o «ID \d{8,}» junto a «plataforma»/«fecha orden»);
  va antes de la regla «venta». En `leer_texto`, con categoría «comandas» el tipo «rappi» NO se fuerza a venta (es de la misma familia).
  `parse_rappi` → doc `tipo="venta"`, `rappi=True`, `numero` = ID, `consumo`/`valor`/`transf` = «Total sugerido a facturar»
  (si no se lee: «Subtotal» con aviso; si tampoco: 0 + aviso «No se leyó el total de Rappi», nunca inventado), `medio="Rappi"`,
  `tercero="Rappi"`. La fecha sigue la regla de la carpeta (la «Fecha orden» impresa no manda).
  — done when: probar_contable +3 checks: texto del papel real → numero 1000000001, valor 25.000, medio Rappi; `construir` de un día
  con ese papel → fila 13452501 débito 25.000 tercero Rappi medio App, débito = crédito; papel sin total → valor 0 + aviso. Suites verdes.
  — files: `parser_module/contable/documentos.py` (detectar_tipo, leer_texto, PARSERS, FAMILIA), `probar_contable.py`
  — hecho: tipo «rappi» (detectar_tipo, parse_rappi, FAMILIA comandas), no se fuerza a venta en «comandas»; probar_contable +3 checks; suites verdes
- [x] T2 (S) ID de Rappi fuera de la numeración + duplicado — R1, R2 — model: Sonnet
  — las comandas con `rappi=True` no entran a los huecos/rangos de comandas (`asientos.py:89,96,426`, `relectura.py:121,200`):
  un helper `_es_comanda(d)` en vez de repetir el filtro. El duplicado por número (`asientos.py:160`) ya cubre «mismo ID = 1 venta»;
  verificar que deja `contar=False` + aviso en el segundo.
  — done when: probar_contable +2 checks: día con comandas 85318–85319 + papel Rappi → sin faltantes ni rangos raros por el ID;
  mismo ID dos veces → una sola fila 13452501 y aviso de duplicado. probar_relectura / probar_faltantes / probar_validar verdes.
  — files: `parser_module/contable/asientos.py`, `parser_module/contable/relectura.py`, `probar_contable.py`
  — hecho: `_es_comanda` en asientos (faltantes, fuera_de_secuencia, aviso de secuencia) y relectura (_nums, sin número); mismo ID de Rappi = duplicado (contar=False, «duplicado de»); probar_contable +2 checks; suites verdes
- [x] T3 (S) Respaldo antes de recalcular — R3 — model: Sonnet
  — `_guardar_libro` copia a `datos/libro.antes-v1.4.0.json` (no a la de v1.3.0): sacar la versión a una constante (o leer `VERSION`)
  para no tocar el código en cada ciclo. Una sola vez, no se pisa.
  — done when: prueba con libro temporal: primera escritura crea el respaldo idéntico, la segunda no lo toca; la copia de v1.3.0 sigue igual.
  — files: `app.py` (`_guardar_libro`), `probar_contable.py`
  — hecho: constante `VERSION_RESPALDO = "1.4.0"` en app.py (respaldo `libro.antes-v1.4.0.json`); probar_contable +1 check (copia v1.3.0 intacta); suites verdes
- [x] T4 (S) Medir septiembre — aceptación — model: Sonnet
  — script de una vez (scratch, no en el repo) sobre una COPIA de `datos/libro.json`: re-leer los papeles de Rappi desde su texto
  guardado, lista papel por papel (fecha, ID, valor, aviso) y suma 13452501 de sept. contra el manual (≈ [01f]); explicar la diferencia.
  Las ventas que no son de Rappi: mismas filas que antes (diff del libro sin los papeles Rappi = vacío).
  — done when: tabla en `docs/sdlc/06-test-report.md` (≤ 40 líneas, cifras sin datos sensibles) + suites verdes.
  — files: ninguno del código; `docs/sdlc/06-test-report.md`
  — hecho: 21 papeles (18 ID) en 13 días; 13452501 sept = [01f] vs ≈ [01f] manual (faltan papeles de 17 días, no es lectura); no-Rappi igual salvo ajuste al cierre 13809501 (4 días) y 28150502 del 11-sep; suites verdes.

## Iteración 1 · defectos de 6-test (2026-10-19)
- [x] FIX-1 (S) El papel de Rappi pierde ID y valor al subir la foto — R1 — model: Sonnet
  — `relectura.leer_hoja` (`un_trozo`, l. 175): un recorte con UNA venta pasa por `leer_recibo`, que re-parsea con `parse_venta`
  → sale venta sin número, valor 0, medio vacío, «dudoso». Probado con motor falso que devuelve el papel: `rappi=None, numero='', valor=0`.
  Las pruebas de T1–T4 llamaban a `leer_texto`/`parse_rappi` directo y no pasaban por aquí. Arreglo: si el doc es `rappi`, no ir a
  `leer_recibo` (o pasarle `parsear=parse_rappi`).
  — done when: probar_relectura +1 check: `leer_hoja([img], motor→papel Rappi, "comandas")` → rappi, ID 1000000001, valor 25.000,
  medio Rappi, estado «validado». Suites verdes.
  — files: `parser_module/contable/relectura.py`, `probar_relectura.py`
  — hecho: `un_trozo` ya no manda el papel Rappi a `leer_recibo`; lo valida `_motivos_rappi` (solo ID y valor, sin hora/mesa); probar_relectura +2 checks; 18/18 suites verdes.
- [ ] FIX-2 (S) `validar` marca «dudoso» todo papel de Rappi (Falta la hora / Falta la mesa) — R1 — model: Sonnet
  — `validar.validar` (l. 165) trata el papel como comanda del POS. Para `rappi=True`: no pedir mesa; hora = la de «Fecha orden»
  (parse_rappi puede llenarla) o no pedirla. Sigue pidiendo ID y valor.
  — done when: probar_validar +1 check: papel Rappi completo → `validar` = []; sin ID → «Falta el número de recibo». Suites verdes.
  — files: `parser_module/contable/validar.py`, `parser_module/contable/documentos.py` (hora), `probar_validar.py`

Riesgo vivo: la foto mezcla comandas y papel Rappi en una sola imagen (`85319-318-rappi.jpg`); `orientacion.py:162` ya tolera
una columna de más. Si el OCR parte mal el papel, T1 lo marca con aviso; no se arregla el corte en este ciclo.
