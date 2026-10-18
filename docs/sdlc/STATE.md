# SDLC state

project: ingresos_app · precisión del OCR
goal: Bajar el margen de error del OCR de recibos (hoy ≈40 % necesita corrección) con validación, relectura con variantes y revisión con foto, medido contra un conjunto de referencia; a futuro, un modelo afinado con nuestros recibos.
size: M      # varios días; toca ocr_module y el parser; sin datos externos nuevos
exposed: no  # app Flask local en 127.0.0.1
regulated: no
next: 5-implement   # plan 2026-10-18

## Stages
- [x] 0-triage       (propuesto 2026-10-17; preguntas abiertas en el log)
- [x] 1-research     → 01-research.md
- [x] 2-requirements   (aprobado 2026-10-17)
- [x] 3-design         (aprobado 2026-10-18) → 03-design.md + ADR-005..007
- [x] 4-plan           → 04-plan.md (16 tareas, 4 iteraciones)
- [ ] 5-implement      current task: T5 (recortes.py + GET recorte)
- [ ] 6-test
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
