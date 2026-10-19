# 04 · Plan — M-13 recibos omitidos

## Summary
- 3 iteraciones, 11 tareas, ≈ 11 h. I1 (≈ 5 h): anotar «falta N» a mano en ④ de punta a punta (R1, R2) + fitness ADR-008.
  I2 (≈ 3,5 h): nombre acortado (R3), causa por pieza en `medir` (R4), consejos en el LEEME (R6). I3 (≈ 2,5 h, con compuerta): R5.
- Orden: lógica pura con su prueba → servidor → ④ → avisos. Cada tarea deja `probar_*.py` en verde (N4).
- Compuerta en T10: si `por_causa` de T8 dice que casi todos los omitidos son de `tipo` (no de `número`), R5 se replantea con el usuario
  antes de implementarlo (riesgo 3 del diseño).
- Seguridad (exposed no): validación de `fecha`/`id`/cuerpo/lista blanca va en T4, no al final.

## Iteración 1 — demo: una foto con un recibo omitido → ④ «Faltan» → «Anotar» con la foto al lado → queda en el libro
- [x] T1 (M) `faltantes.py` puro: `crear`, `anotar`, `cerrar`, `abiertos`, `reconciliar` con el esquema del marcador (diseño §4)
  — R1 — done when: `probar_faltantes.py` nuevo pasa (crear desde números y desde nombre no entendido; anotar → venta manual con
  `de_foto`; cerrar con motivo ≤ 200; reconciliar: anotado y no_existe no vuelven, abierto sí) — files: `parser_module/contable/faltantes.py`,
  `probar_faltantes.py` — model: Sonnet — hecho: faltantes.py puro (crear/anotar/cerrar/abiertos/reconciliar), 15 checks en probar_faltantes.py
- [x] T2 (M) Fitness ADR-008 + barrido de `tipo`: asientos, Excel, crudo, `validar.faltantes` y `medir` iguales con y sin marcador — hecho: marcador excluido de contar (asientos.marcar_duplicados), sin fila en DATOS OCR, "faltante" aceptado en TIPOS_CRUDO; 5 checks en probar_contable; validar.faltantes y medir ya filtraban venta
  — R1, riesgo 1 — done when: prueba en `probar_contable.py` (asientos y filas de Excel idénticos con un marcador en el día) pasa;
  `grep 'tipo'` en `asientos.py`, `exportar.py`, `excel_export.py`, `soporte*.py` revisado y lo que no filtra `venta` corregido
  — files: `probar_contable.py`, `parser_module/contable/asientos.py`, `parser_module/contable/exportar.py`, `excel_export.py` — model: Sonnet
- [x] T3 (M) `relectura.leer_hoja` devuelve `falta`; `app._leer_hoja` guarda la foto entera (`recortes.guardar`, ≤ 1600 px) solo si hay
  faltante y añade los marcadores; `_conservar_revisados` pasa por `reconciliar` — R1 — done when: `probar_relectura.py` cubre `falta`
  y `probar_revision.py` cubre releer una foto ya resuelta sin marcador duplicado; foto sin guardar → `recorte:null`
  — files: `parser_module/contable/relectura.py`, `app.py` (`_leer_hoja` ≈ l.280, `_conservar_revisados` ≈ l.388), `probar_relectura.py`,
  `probar_revision.py` — model: Sonnet — hecho: leer_hoja devuelve `falta` (ints); app._marcadores_de_foto guarda la foto ≤1600 px y crea marcadores; _conservar_revisados reconcilia; 3 checks en probar_relectura + 7 en probar_revision
- [x] T4 (M) API: `GET /api/contable/revision?estado=falta`, `POST …/<fecha>/<id>/anotar` y `…/no_existe` bajo `LOCK` + `_bloqueos`
  — R1 — done when: `probar_revision.py` prueba anotar, no_existe, 409 en día transmitido, 400 con fecha/id malos, cuerpo > 64 KB,
  campo fuera de lista blanca, motivo > 200, y «anotar» sobre una venta normal → 400 — files: `app.py` (≈ l.408–460), `probar_revision.py`
  — model: Sonnet — hecho: GET estado=falta, POST anotar y no_existe (helpers `_campos_revision`, `_cambiar_faltante`; lista blanca compartida con confirmar, sin id ni fecha; anotar rellena con `_base("venta","")`); +34 checks en probar_revision
- [x] T5 (M) ④ selector «Faltan»: tarjeta con la foto entera (o «sin foto guardada» + nombre), formulario manual con el número puesto,
  botones «Anotar» y «No existe» (motivo); insignia de ④ con los abiertos; ① muestra el marcador como fila de solo lectura «falta».
  Todo con `textContent`/DOM (T11); reglas `@media` de teléfono y tableta (ancho y alto) — R1 — done when: en el navegador, una foto
  de prueba con faltante se anota y el aviso desaparece; «No existe» lo cierra; captura de pantalla — files: `static/contable.html` — model: Sonnet
  — hecho: opción «Faltan» en `#rv_est`, `tarjetaFalta` (foto o «Sin foto guardada»), Anotar/No existe con validación en cliente; `#b4` = dudosos + faltan; ① fila `tr.falta` de solo lectura; @media teléfono/tableta/apaisado. Verificado en el navegador con datos temporales
- [x] T6 (S) Aviso R2: «quedan N recibos sin anotar» en «Pasar al libro» y en «⬇ Excel» (`confirm()`, no bloquea) — R2 — done when:
  con 1 faltante abierto sale el aviso y se puede seguir; con 0 no sale — files: `static/contable.html` — model: Sonnet
  — hecho: `avisoFaltan()` (refresca abiertos con `insigniaRev`; `confirm()` solo si N>0, cancelar no sigue, aceptar sí) al inicio de «Pasar al libro» y «⬇ Excel (MOVIMIENTOS)»

- [x] FIX-1 (S) R2 en «Pasar al libro» también cuenta los marcadores abiertos del día en pantalla (`docs`), no solo los del libro
  — R2 — done when: escanear (o simular) un día con 1 marcador en `docs` y 0 en el libro → sale el aviso; 0 y 0 → nada
  — files: `static/contable.html` (`avisoFaltan`, `$("conf")`) — model: Sonnet
  — hecho: `avisoFaltan(enPantalla)` suma `docs` con tipo faltante y estado falta solo desde «Pasar al libro»; Excel sigue contando solo el libro
- [x] FIX-2 (S) `_conservar_revisados`: la venta anotada a mano (`origen:"manual"`, `de_foto`) empareja con la relectura OCR del mismo
  número y foto (clave con `de_foto`) → no se cuenta dos veces — R1 — done when: probar_revision prueba previo manual 85388/F +
  nuevo OCR 85388/F → una sola venta (la manual); todas las probar_*.py en verde — files: `app.py`, `probar_revision.py` — model: Sonnet
  — hecho: la clave de `_conservar_revisados` usa `de_foto` como origen cuando `origen=="manual"`; 1 check nuevo en probar_revision

## Iteración 2 — demo: la foto «85334-338 al 3341-343» corta en 6 y `medir --completo` dice la causa de cada omitido
- [ ] T7 (M) `validar.leer_nombre` → `Nombre(numeros, correcciones, entendido)`; corrección por sufijo con aviso «3341 → 85341»;
  `numeros_de_nombre` queda como envoltorio; nombre no entendido → marcador «No entiendo el nombre de la foto …» (vía `faltantes.crear`)
  — R3, ADR-009 — done when: `probar_validar.py` da para la foto 3 exactamente 85334, 85338–85341, 85343 con aviso; nombres de la
  referencia sin cambio; nombre basura → marcador, no 1 pieza callada — files: `parser_module/contable/validar.py`,
  `parser_module/contable/relectura.py`, `app.py`, `probar_validar.py` — model: Sonnet
- [ ] T8 (M) `referencia.medir` guarda `piezas` (tipo, número, 120 caracteres) y `causa_de` pura; informe con `omitidos_detalle` y
  `por_causa`; `medir_precision.py` lo imprime — R4 — done when: `probar_precision.py` prueba `causa_de` para tipo/corte/número;
  `medir_precision.py --completo` sobre septiembre imprime `por_causa` y la suma = omitidos — files: `parser_module/contable/referencia.py`,
  `medir_precision.py`, `probar_precision.py` — model: Sonnet
- [ ] T9 (S) LEEME: sección «Cómo tomar la foto» (fondo oscuro liso, una columna, cerca, sin cortar el pie) ≤ 8 líneas — R6 — done when:
  la sección existe y tiene ≤ 8 líneas — files: `LEEME-contador.md` — model: Haiku

## Iteración 3 — demo: `medir --completo` con omitidos (solo OCR) ≤ 2/107 sin empeorar aciertos ni dudosos
- [ ] T10 (S) Compuerta R5: correr `medir --completo` (tras T7–T8), anotar `por_causa` en STATE y decidir con el usuario si R5 sigue
  tal cual — R5, riesgo 3 — done when: STATE tiene la línea con la cifra y la decisión — files: `docs/sdlc/STATE.md` — model: Sonnet
- [ ] T11 (M) R5 en `leer_hoja`: solo si hay faltantes, recortar la cabecera de cada pieza sin número válido, ampliar ×2,
  `numeros_tesseract`; exactamente un faltante → se asigna con nota y `estado:"dudoso"`; Tesseract ausente → se salta (ADR-010)
  — R5, N2, N3 — done when: `probar_relectura.py` cubre asignar/no asignar (0 o 2 coincidencias)/sin Tesseract; `medir --completo`
  omitidos ≤ 2/107, aciertos y dudosos ≥ M-12, tiempo por foto ≤ 1,2 × M-12; todas las `probar_*.py` pasan
  — files: `parser_module/contable/relectura.py`, `ocr_module/digitos.py`, `probar_relectura.py` — model: Opus
