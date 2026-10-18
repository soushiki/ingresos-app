# SDLC state

project: ingresos_app · precisión del OCR
goal: Bajar el margen de error del OCR de recibos (hoy ≈40 % necesita corrección) con validación, relectura con variantes y revisión con foto, medido contra un conjunto de referencia; a futuro, un modelo afinado con nuestros recibos.
size: M      # varios días; toca ocr_module y el parser; sin datos externos nuevos
exposed: no  # app Flask local en 127.0.0.1
regulated: no
next: 5-implement   # iteración 5: FIX-1..11 + R3b (06-test-report)
current task: FIX-9 hecho (sin commit); sigue FIX-10

## Stages
- [x] 0-triage       (propuesto 2026-10-17; preguntas abiertas en el log)
- [x] 1-research     → 01-research.md
- [x] 2-requirements   (aprobado 2026-10-17)
- [x] 3-design         (aprobado 2026-10-18) → 03-design.md + ADR-005..007
- [x] 4-plan           → 04-plan.md (16 tareas, 4 iteraciones)
- [x] 5-implement      T1–T16 hechos (T16: metas N3 no cumplidas, ver 08-maintenance)
- [x] 6-test         → 06-test-report.md (suite verde; 10 hallazgos → FIX-1..10)
- [ ] 7-release
- [ ] 8-maintain

(Mark skipped stages `- [~]`.)

## Ciclo anterior
- Documento soporte: v1.0.1 publicada; su STATE está en `archive/documento-soporte/STATE.md`. Pendientes de mantenimiento en `08-maintenance.md` (cruce de efectivo con el manual, extracto 24–30, Rappi #6, #2/#4).

## Decisiones de triage (propuestas, 2026-10-17)
- Usuario: menos errores importa más que la velocidad; acepta más tiempo por foto.
- Usuario: a futuro, un modelo que se acostumbre a estos recibos y prediga valores de los mal impresos → fase 2 (LoRA), con el catálogo de precios como primer paso sin entrenamiento.
- Confirmado por el usuario (2026-10-17): alcance = piezas A–F; solo motores locales (qwen2.5vl + Tesseract para dígitos); recibo dudoso = cuenta con el valor más probable y va a revisión; LoRA = fase 2.

## Log
<!-- YYYY-MM-DD | stage | one-line result -->
2026-10-17 | 0-triage | Ciclo nuevo «precisión del OCR», tamaño M, exposed no; ciclo documento soporte archivado (STATE en archive/)
2026-10-17 | 1-research | 2 scouts + datos del mes: ≈40 % de recibos corregidos (96 omitidos); validación por recibo + relectura con variantes + Laplaciano; binarizar puede empeorar al VLM; catálogo de precios; LoRA fase 2 → 01-research.md
2026-10-17 | 2-requirements | Borrador R1–R10 (Must R1, R2, R5, R7, R8, R9), N1–N5, 3 preguntas abiertas → 02-requirements.md; gate pendiente
2026-10-17 | 2-requirements | Aprobado por el usuario: R1–R10, N1–N5; N3 sirve, septiembre solo como prueba, máx. 3 relecturas
2026-10-18 | 3-design | Borrador: bucle leer→validar→releer en servidor (ADR-005), recortes por huella (ADR-006), referencia congelada (ADR-007); 3 riesgos; gate pendiente
2026-10-18 | 3-design | Aprobado por el usuario: 03-design.md y ADR-005..007
2026-10-18 | 4-plan | 16 tareas en 4 iteraciones (≈20 h); línea base N3 y spike C3 primero; crudo sigue version 1 (anidado 5 ≤ 6) → 04-plan.md
2026-10-18 | 5-implement | T1: referencia.py + medir_precision.py + probar_precision.py (9 checks); suite verde; corrida real de línea base pendiente (fotos de sept. + Ollama)
2026-10-18 | 5-implement | T2: parse_venta saca items/subtotal/pagado/cambio/hora; subtotal 95,3 % (450/472) sobre OCR guardado de sept.; suma de ítems = subtotal solo 71,6 % → regla de ítems de T3 con tolerancia/aviso
2026-10-18 | 5-implement | T3: validar.py puro (4 campos + 4 sumas, tolerancia 0, regla_items apagable); probar_validar.py 16 checks; aún sin llamar (T8)
2026-10-18 | 5-implement | T4: estado_de(d) migra al leer (revisado viejo → «revisado», avisos → «dudoso», si no «validado»); _base usa estado; lectura completa ida y vuelta por crudo v1 (anidado 5); ojo T10: referencia.py:31 aún lee `revisado`
2026-10-18 | 5-implement | T5: recortes.py (huella sha256[:16], gris JPEG) + GET /api/contable/recorte/<nombre> con 404 por patrón; probar_recortes 17 checks; suite verde; iteración 1 completa → f389140
2026-10-18 | 5-implement | T6: preprocess.variantes (V0–V3) + nitidez (Laplaciano + Tenengrad, numpy, ≤1000 px); probar_variantes 12 checks; suite verde
2026-10-18 | 5-implement | T7: relectura.leer_recibo (V0→validar→≤3 relecturas, voto por campo, borrosa pide par que coincida, tope de tiempo, MOTOR_LOCK, recorte C6); probar_relectura 28 checks; umbral_laplaciano=100 sin calibrar (T9)
2026-10-18 | 5-implement | T8: relectura.leer_hoja + R5 en validar (numeros_de_nombre, fuera del nombre, faltantes, cruces); 2 fotos reales leídas en la app; separar deja 30/40 fotos en una pieza → usuario aprueba spike T8b antes de T9
2026-10-18 | 5-implement | T8b: separar(img, esperados=n) por columnas + huecos más anchos, sin bordes de papel; cuenta exacta 1/43 → 35/43 (81 %), a ojo ≈29/43 limpias; VLM y máscara de papel descartados; falla madera/mesa oscura y fotos de lado; sin esperados idéntico; probar_separar 9 checks
2026-10-18 | 5-implement | T8b conectado: app._leer_hoja y medir_precision pasan esperados del nombre; la foto 1/85297 al 85302 sale en 6 recortes; suite verde
2026-10-18 | 5-implement | T9: V4 Real-ESRGAN opcional + medir_precision --variantes/--peores; 20 fotos más dudosas: V0 59/107 enteros bien, suman V4 +9, V3 +4, V1 +1, V2 0 → config V0,V4,V3,V1,V2; iteración 2 completa
2026-10-18 | 5-implement | T10: GET/POST /api/contable/revision (400/404/413), confirmar/editar → «revisado» + recalcula el día + referencia.agregar; cont_confirmar conserva revisados al releer; referencia.congelar usa estado_de; probar_revision 38 checks; suite verde
2026-10-18 | 5-implement | T11: pestaña ④ Revisión (recorte, motivo, pasadas, candidatos clicables, confirmar/editar) + @media ancho/alto; probada en navegador: corregir 85299 recalcula el 01/09; 375 px sin scroll; datos restaurados
2026-10-18 | 5-implement | T12: DATOS OCR suma columnas Recibo (estado_de) y Motivo; fila amarilla si dudoso; avisos del día con motivo de cada venta dudosa (revisado no avisa); probar_datos_ocr +6 checks; suite verde; tocó asientos.py/exportar.py en vez de excel_export.py
2026-10-18 | 5-implement | T13: digitos.numeros_tesseract (lista blanca, sin Tesseract → None + aviso) + R3 en validar (ctx["digitos"]; None → se salta); probar_digitos 10 checks; suite verde; OJO: relectura aún no pasa ctx["digitos"] → cablear en T14/T16
2026-10-18 | 5-implement | T14: catalogo.py ({auto,manual} en datos/catalogo.json, manual gana; cargar/reconstruir/desde_libro) + R6 en validar (precio ≠ carta → dudoso; línea ilegible → «precio sugerido», no reemplaza); probar_validar +8 checks; suite verde; OJO T16: nadie llama desde_libro y relectura/app no pasan ctx["catalogo"] ni ctx["digitos"]
2026-10-18 | 5-implement | T15: referencia.exportar_entrenamiento (jpg + json por recibo; sin recorte → lista sin_recorte) + recortes.borrar_huerfanos + medir_precision --exportar/--borrar-recortes/--borrar-huerfanos; probar_entrenamiento 6 checks; suite verde; flags CLI sin correr
2026-10-18 | 5-implement | T16: --completo + R3/R6 cableados; 107 recibos: con error 12,2→3,4 %, omitidos 15,9→16,8 %, dudosos 20→58 (35 falsa alarma, R3 ciego en recorte entero); metas N3 no cumplidas; LEEME §7 fotos; 01d fuentes OCR + spike Google Vision preparado (tapa NIT/dirección/tel./domicilio/<NOMBRE>)
2026-10-18 | 5-implement | Spike 2d Google Vision (5088d61): no lee mejor que qwen; rearmar por filas sí importa; 15 «errores» son de la referencia. R3 cambiado por el usuario (02-requirements): no ver → nota suave; distinto con contexto → dudoso; a implementar tras 6-test
2026-10-18 | 6-test | It. 1–4: 17 suites verdes; R-ids cubiertos salvo N4 y R3b; code-review high 10 hallazgos (peor: releer pierde «revisado») → it. 5 FIX-1..11 + R3b; smoke pendiente del usuario
2026-10-18 | 5-implement | FIX-13 (pedido antes de la it. 5): revisado sin ⚠ ni Motivo viejo, aviso → avisos_resueltos; suite verde; 85313 «✓ revisado» en la app
2026-10-18 | 5-implement | FIX-1: _conservar_revisados agrega el revisado que la relectura no trae y no reusa un previo; probar_revision +4 checks; suite verde
2026-10-18 | 5-implement | FIX-2: medir cuenta dudoso por estado_de, no por avisos; probar_precision +2 checks; suite verde; re-corrida T16 pendiente (informes sin estado → requiere re-OCR de 107 recibos)
2026-10-18 | 5-implement | FIX-3: voto que valida sin candidato entero → motivo propio SIN_CANDIDATO (sigue dudoso), ya no los motivos de V0; probar_relectura +4 checks; suite verde
2026-10-18 | 5-implement | FIX-4: «Falta la mesa» no aplica si domicilio > 0 o detalle dice domicilio/llevar (sin tildes); probar_validar +4 checks; suite verde
2026-10-18 | 5-implement | FIX-5: regla_items apagada por defecto (CONFIG), se enciende por ctx; probar_validar +1 check; suite verde
2026-10-18 | 5-implement | FIX-6: fecha ya no es editable en Revisión (400); probar_revision +2 checks; suite verde
2026-10-18 | 5-implement | FIX-7: recortes.guardar renueva el mtime al reusar un recorte (borrar por rango ya no se lo lleva); probar_recortes +2 checks; suite verde
2026-10-18 | 5-implement | FIX-8: lector_completo pasa completa=False en páginas de un PDF de varias páginas (como app.py); probar_precision +1 check; suite verde
2026-10-18 | 5-implement | FIX-9: _catalogo en memoria (una vez por arranque), confirmar en Revisión lo invalida; probar_revision +2 checks; suite verde
