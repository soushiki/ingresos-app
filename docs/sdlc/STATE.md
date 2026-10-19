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
- [ ] 5-implement      current task: T11 (R5 en leer_hoja, I3)
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
2026-10-18 | 5-implement | T1 faltantes.py puro + probar_faltantes.py (15 comprobaciones); todas las probar_*.py en verde. Ojo T4: lista blanca debe excluir id/fecha de campos
2026-10-18 | 5-implement | T2 fitness ADR-008: marcador fuera de contar y de DATOS OCR, "faltante" en TIPOS_CRUDO; 6 checks en probar_contable; todas las probar_*.py en verde
2026-10-18 | 5-implement | T3 leer_hoja devuelve falta; _leer_hoja añade marcadores con foto entera ≤1600 px (recorte null si falla); _conservar_revisados reconcilia; confirmar conserva no_existe. Ojo T4: anotar debe rellenar campos con _base("venta") (si no, KeyError en asientos); lista blanca sin id/fecha
2026-10-18 | 5-implement | T4 API revision?estado=falta, …/anotar y …/no_existe bajo LOCK+_bloqueos; lista blanca compartida _campos_revision (sin id/fecha); ~34 checks en probar_revision; todas las probar_*.py en verde
2026-10-18 | 5-implement | T5 ④ «Faltan»: tarjeta con foto/«sin foto», Anotar (día +25.000 cuadra) y No existe (motivo obligatorio) probados en el navegador con datos temporales; insignia ④ = dudosos+faltan; fila «falta» en ①; arreglado botón de 140 px en teléfono (flex:none)
2026-10-18 | 5-implement | T6 aviso R2 (confirm, no bloquea) en «Pasar al libro» y «⬇ Excel»; verificado en navegador con fetch simulado (1 → aviso, 0 → nada); iteración 1 completa → 6-test
2026-10-18 | 6-test | I1: 18/18 probar_*.py en verde; revisión → FIX-1 (R2 no avisa del día en pantalla) y FIX-2 (venta manual + relectura OCR = doble); smoke pendiente → 06-test-report.md
2026-10-18 | 5-implement | FIX-1 avisoFaltan(enPantalla) suma los marcadores abiertos de `docs` en «Pasar al libro» (Excel sigue solo libro); verificado en navegador (1 en pantalla → aviso, 0 → nada); 18/18 probar_*.py en verde
2026-10-18 | 5-implement | FIX-2 clave de _conservar_revisados usa de_foto si origen==manual (venta anotada + relectura OCR = una sola); prueba en probar_revision; 18/18 probar_*.py en verde
2026-10-18 | 6-test | I1 segunda pasada PASS: 18/18 probar_*.py en verde, FIX-1/FIX-2 cerrados; menor aceptado (re-pasar un día del libro cuenta su marcador 2 veces en el aviso); smoke de 5 pasos para el usuario en 06-test-report.md → 5-implement T7
2026-10-18 | 5-implement | T7 leer_nombre → Nombre(numeros, correcciones, entendido); foto 3 = 85334, 85338–341, 85343 con aviso «3341 → 85341»; nombre basura (≥4 cifras) → marcador; 18/18 probar_*.py en verde
2026-10-18 | 5-implement | T8 causa_de pura + piezas/omitidos_detalle/por_causa en medir; 7 checks en probar_precision; 18/18 en verde. Septiembre (224 recibos): omitidos 42 = corte 25 + número 17 + tipo 0; los «corte» son sobre todo PDF sin esperados (nombre = fecha de escaneo) → revisar en T10
2026-10-19 | 5-implement | T9 LEEME §7 «Cómo tomar la foto» (6 líneas: fondo oscuro liso, una columna, cerca, sin cortar el pie); reemplaza el consejo viejo de fondo claro; nombre con números completos; «Falta N» en ④; 18/18 probar_*.py en verde; iteración 2 completa → 6-test
2026-10-19 | 6-test | I2: 18/18 probar_*.py en verde; R4 y R6 cumplen; R3 → FIX-3 (los PDF del escáner `comandas2026…_hhmmss.pdf` y las fotos IMG_ dan un marcador «No entiendo» falso) y FIX-4 (el marcador sin número se duplica al releer) → 06-test-report.md
2026-10-19 | 5-implement | FIX-3 entendido=False solo si el nombre empieza por un recibo (4–6 cifras); ≥7 cifras o AAAA-MM-DD → sin R5 ni marcador; de los 62 nombres solo cambian los 11 PDF del escáner. FIX-4 clave ("faltante","",origen) → un «No entiendo» por foto al releer; 18/18 probar_*.py en verde → 6-test I2
2026-10-19 | 6-test | I2 segunda pasada PASS: 18/18 probar_*.py en verde, FIX-3/FIX-4 cerrados; menor aceptado (nombre con recibos + fecha → sin R5); smoke de 5 pasos para el usuario → 5-implement T10
2026-10-19 | 5-implement | T10 compuerta: medir --completo --peores 20 (informe 20261019-052322, 4 h 09 min) → 103 recibos (antes 107: T7 cambió los esperados de la foto 3), omitidos 13 = número 13 + corte 0 + tipo 0; dudosos 18, validados con error 7. Todos son de número → R5 aplica tal cual; espera decisión del usuario. Ojo: 4 omitidos en 5/85387 al 392; N3 pide ≤ 2/103
2026-10-19 | 5-implement | T10 decisión del usuario: R5 sigue tal cual (ADR-010) → T11
