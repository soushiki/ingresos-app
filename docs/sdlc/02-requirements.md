# 02 · Requisitos — Precisión del OCR

## Summary
- Meta: que el OCR de comandas deje de necesitar corrección en ≈40 % de los recibos. Cada recibo se valida solo; lo que no valida se relee con variantes de imagen, y lo que sigue sin validar va a revisión con su foto. Todo se mide contra un conjunto de referencia.
- Musts principales: R1 validación por recibo, R2 relectura con variantes y voto, R8 cola de revisión con foto.
- NFR clave: todo local (N1). Se acepta hasta ~3× el tiempo actual por foto (N2) a cambio de los objetivos de precisión de N3.
- Decidido por el usuario (2026-10-17): piezas A–F de 01-research; solo motores locales (qwen2.5vl + Tesseract para dígitos); el recibo dudoso cuenta con el valor más probable y va a revisión; el modelo afinado (LoRA) es la fase 2.

## Stories
- **R1 (Must) Validar cada recibo.** Como contador, quiero que la app revise la aritmética de cada comanda, para que un número mal leído no entre sin aviso.
  - Dado un recibo leído, cuando los ítems no suman el subtotal, o subtotal − descuento + domicilio ≠ total a pagar, o total + propina ≠ pagado, o pagado − cambio ≠ efectivo (con tolerancia configurable, por defecto 0), entonces queda «dudoso» con el motivo exacto.
  - Dado un recibo sin número, sin hora, sin mesa o sin medio de pago, entonces queda «dudoso» con el campo que falta.
- **R2 (Must) Releer con variantes y votar.** Como contador, quiero que un recibo dudoso se lea otra vez de otra forma, para que la app se corrija sola antes de molestarme.
  - Dado un recibo dudoso por R1, R3, R4 o R5, cuando se relee hasta N veces (por defecto 3) con variantes de imagen (tamaño, contraste, recorte), entonces cada campo toma el valor que más se repite. Si un candidato pasa R1, gana ese.
  - Se guarda qué variante dio cada valor y cuántas pasadas se hicieron.
- **R3 (Should) Cruzar dígitos con Tesseract.** Como contador, quiero un segundo lector para los números, para que dos lecturas independientes tengan que coincidir.
  - Dado un recibo, cuando Tesseract lee distinto el número de recibo, el total o lo pagado, entonces queda «dudoso» y se relee (R2).
  - *Cambio aprobado por el usuario 2026-10-18 (T16: Tesseract sobre el recorte entero ve el número en 2/12; 35 falsas alarmas):*
    (a) **distinto con contexto** (nombre de la foto R5, sumas R1) → «dudoso», como arriba; (b) **no lo ve** → nota suave
    «sin confirmar por segundo lector», visible en Revisión pero sin marcar «dudoso», salvo que otra regla también falle;
    (c) cuando el lector por línea (01d-2c) vea el valor impreso en ≥ 90 % de los casos, (b) pasa a «dudoso». Siguiente ciclo, tras 6-test.
- **R4 (Should) Detectar foto borrosa.** Como contador, quiero que la app sepa cuándo una foto es mala, para que la lea con más cuidado.
  - Dada una foto o un recorte, se calculan la nitidez (varianza del Laplaciano) y el tiempo de OCR. Bajo el umbral (configurable, calibrado con N3), la foto recibe más pasadas y un aviso «foto borrosa».
  - Los dos valores quedan guardados por papel, para calibrar el umbral.
- **R5 (Must) Revisar la foto completa.** Como contador, quiero saber si en una foto faltan recibos o vienen pegados, para que ninguna venta se pierda.
  - Dado un recorte con dos membretes, entonces se separa (sigue la línea de M-9).
  - Dada una foto cuyo nombre trae un rango (p. ej. «85560 al 565»), cuando falta un número del rango o sobra uno fuera de él, entonces aparece el aviso «falta el recibo 85563 en esta foto» y se re-segmenta y relee la foto.
  - Dos recibos de la misma foto con montos idénticos y distinta mesa u hora quedan dudosos (posible cruce de valores entre vecinos).
- **R6 (Should) Catálogo de precios.** Como contador, quiero que la app conozca la carta, para que una línea mal impresa se pueda deducir.
  - El catálogo producto → precio se arma desde los recibos validados y se puede editar.
  - Dado un ítem cuyo precio no coincide con el catálogo, entonces queda dudoso. Dada una línea ilegible con producto reconocido, se propone el precio de la carta marcado «sugerido». Nunca reemplaza en silencio un valor leído.
- **R7 (Must) Recibo dudoso.** Como contador, quiero que lo dudoso no detenga el día pero se note.
  - Dado un recibo que sigue dudoso tras R2, entonces cuenta en el libro con el valor más probable, con estado «dudoso» y aviso en el día, en DATOS OCR y en el Excel.
  - Un recibo «revisado» a mano nunca se sobrescribe al releer.
- **R8 (Must) Cola de revisión con foto.** Como contador, quiero ver juntos el recorte y lo leído de cada dudoso, para que corregir tome segundos.
  - La pestaña de revisión lista los dudosos con su recorte, los valores, los candidatos de cada pasada y el motivo. Al confirmar o editar, el recibo pasa a «revisado», el día se recalcula y el recibo entra al conjunto de referencia (R9).
- **R9 (Must) Medir la precisión.** Como dueño, quiero una cifra de cuántos errores comete el OCR, para que cada cambio se juzgue con datos.
  - Los recibos «revisado» de septiembre (≈227) más la foto de cada uno forman el conjunto de referencia.
  - Un script relee esas fotos y reporta la precisión por campo (número, consumo, propina, domicilio, medio, pagos), los recibos omitidos, los dudosos y los «validados con error» (los peores), antes y después de cada cambio.
- **R10 (Could) Datos para la fase 2.** Como dueño, quiero guardar recorte + valores confirmados, para que más adelante se pueda afinar un modelo (LoRA).
  - Se exporta el conjunto de referencia (imagen + JSON de campos) en un formato estándar de entrenamiento.

## Non-functional
- **N1 Local.** Ninguna imagen sale del PC: solo Ollama local + Tesseract. El modo SIN_OCR del PC del contador no cambia.
- **N2 Tiempo.** En promedio, hasta ~3× el tiempo actual por foto; las fotos que validan a la primera no se releen. Se muestra el avance por foto.
- **N3 Precisión (contra R9).** Recibos omitidos ≤ 2 %. Entre los recibos marcados «validado», ≤ 1 % con algún campo malo. Todo error restante cae en «dudoso». Línea base: medirla primero con el lector actual.
- **N4 Reproducible.** Temperatura 0; se registran la variante, la pasada y el motor de cada valor.
- **N5 Datos.** Guardar el recorte de cada recibo (para revisión y fase 2) sin duplicar fotos enteras; borrarlos debe ser posible.

## Out of scope
- Afinar un modelo (LoRA): fase 2. Gemini y cualquier motor en la nube.
- Mejoras para gastos manuscritos y facturas de proveedor (siguen con las reglas actuales). Los papeles de Rappi (01c #6). Cambiar cómo se toman las fotos (solo una guía de captura en el LEEME).

## Open questions
Resueltas por el usuario (2026-10-17, al aprobar):
1. Los objetivos de N3 sirven (≤ 2 % omitidos, ≤ 1 % de validados con error).
2. Septiembre se relee solo como prueba (R9), sin tocar los recibos «revisado».
3. Máximo 3 relecturas por recibo dudoso.
