# SDLC state

project: ingresos_app · recibos omitidos (M-13)
goal: Que ningún recibo de una foto se pierda en silencio: bajar los omitidos de 13/107 (12,1 %) a ≤ 2 % (meta N3) en la referencia congelada de septiembre, con lector y separador 100 % locales.
size: M      # varios días: separar (M-11) + lectura del número por línea + medición; sin datos ni servicios nuevos
exposed: no  # app Flask local en 127.0.0.1
regulated: no
next: 5-implement

## Stages
- [x] 0-triage       (confirmado por el usuario 2026-10-18)
- [x] 1-research     (2026-10-18: 3 corte, 10 cortados bien → número/tipo sin saber)
- [x] 2-requirements   (aprobado por el usuario 2026-10-18)
- [x] 3-design         (aprobado por el usuario 2026-10-18)
- [x] 4-plan          (2026-10-18: 3 iteraciones, 11 tareas, ≈ 11 h)
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
2026-10-18 | 1-research | 13 omitidos: 3 del corte (nombre «3341» sin entender → 1 pieza; 13/85582 columna), 10 bien cortados (número o tipo; falta registro por pieza). Orden: «falta N» en ④ (S) → nombre → registro → lector del número
2026-10-18 | 2-requirements | Borrador 02-requirements.md: R1–R8 (Musts R1 anotar «falta N» en ④, R2 aviso al exportar, R3 nombre acortado, R4 causa por pieza), N1–N5; espera aprobación
2026-10-18 | 2-requirements | Aprobado por el usuario con los 3 valores por defecto: anotados a mano no cuentan para N3; R2 avisa, no bloquea; +20 % de tiempo aceptable
2026-10-18 | 3-design | Borrador 03-design.md + ADR-008 (faltante = documento marcador), 009 (nombre acortado: sufijo + aviso; foto 3 = 85334, 85338–341, 85343), 010 (cabecera ampliada solo con faltantes); espera aprobación
2026-10-18 | 3-design | Aprobado por el usuario tal como está; ADR-008/009/010 aceptados
2026-10-18 | 4-plan | 04-plan.md: I1 R1+R2+fitness ADR-008 (T1–T6, ≈ 5 h), I2 R3+R4+R6 (T7–T9), I3 compuerta R5 (T10) + R5 (T11, Opus)
