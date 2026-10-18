# SDLC state

project: ingresos_app · recibos omitidos (M-13)
goal: Que ningún recibo de una foto se pierda en silencio: bajar los omitidos de 13/107 (12,1 %) a ≤ 2 % (meta N3) en la referencia congelada de septiembre, con lector y separador 100 % locales.
size: M      # varios días: separar (M-11) + lectura del número por línea + medición; sin datos ni servicios nuevos
exposed: no  # app Flask local en 127.0.0.1
regulated: no
next: 1-research

## Stages
- [x] 0-triage       (confirmado por el usuario 2026-10-18)
- [ ] 1-research     (ligera: los 13 omitidos uno por uno → causa: corte, número, lectura)
- [ ] 2-requirements   (gate: user approval)
- [ ] 3-design         (gate: user approval)
- [ ] 4-plan
- [ ] 5-implement      current task: -
- [ ] 6-test
- [ ] 7-release
- [ ] 8-maintain

(Mark skipped stages `- [~]`.)

## Ciclos anteriores
- Documento soporte v1.0.1 → `archive/documento-soporte/`. Precisión del OCR v1.1.0 → `archive/precision-ocr/` (01–07 + STATE).
- Siguen en su sitio: `01d-fuentes-ocr.md` (insumo: lector por línea, rearmar por filas), `08-maintenance.md`, `adr/`.

## Punto de partida (M-12, 2026-10-18; 20 fotos, 107 recibos)
- Omitidos 13: 85387–85390 (una foto, 5/85387 al 392), 85340 y 85343 (3/85334…), 85375, 85411, 85413, 85436, 85442, 85534, 85588.
- M-11 dejó 6 fotos mal cortadas (columna con 3 papeles, pie sin canto, el nombre dice 3 y hay 4). Releer no recupera omitidos.
- Ya existe R5: los números del nombre del archivo que faltan dan aviso «faltantes».
- Solo motores locales (qwen2.5vl, Tesseract, Real-ESRGAN). Google Vision fue un spike de una vez y no entra en la app (cuota gratuita).

## Wrong-road check
Lo más barato: no leer mejor, sino **cerrar el hueco a mano**: R5 ya sabe qué número falta, así que ④ Revisión podría mostrar
«falta el 85388» con la foto entera y un formulario corto para anotarlo (≈ S, sin OCR nuevo). Con eso ningún recibo se pierde aunque
el OCR siga omitiendo; leer mejor solo baja cuántos hay que anotar.

## Log
<!-- YYYY-MM-DD | stage | one-line result -->
2026-10-18 | 0-triage | Ciclo nuevo M-13 «recibos omitidos», tamaño M, exposed no; ciclo precisión OCR archivado (archive/precision-ocr/). Preguntas: (1) meta ≤ 2 % omitidos en la referencia [def. sí]; (2) primero «falta N» a mano en ④ y luego leer mejor [def. los dos, a mano primero]; (3) consejos de foto (fondo oscuro liso, una columna) en el LEEME, sin obligar [def. sí]
2026-10-18 | 0-triage | Confirmado por el usuario: meta ≤ 2 % omitidos (N3); orden = «falta N» a mano en ④ primero, luego mejor corte/lectura; consejos de foto en el LEEME (sin obligar); tamaño M
