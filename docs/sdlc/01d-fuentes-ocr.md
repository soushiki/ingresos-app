# 01d · Fuentes OCR (búsqueda de Google del usuario) vs. nuestro pipeline — 2026-10-18

Fuentes: Google Vision / Document AI, Azure Read + recibo, Amazon Textract, TrOCR, OpenCV, Transkribus (+ alternativas
locales de 2026). Dos scouts; confianza media (precios de Azure/Document AI y cifras de recibos de un solo proveedor sin verificar).

## Summary
- Nada de la lista reemplaza el pipeline; casi todo lo que proponen para limpiar y validar ya lo hacemos.
- Lo único nuevo que vale medir es **otro lector local de recibos: PaddleOCR-VL / PP-OCRv5** (cabe en GPU de casa) y
  **OpenCV perspectiva/deskew**. TrOCR y Transkribus no sirven para comandas térmicas.
- La nube saldría barata (≈ 0–10 USD/mes) pero choca con la decisión «solo motores locales» (triage 2026-10-17). Solo el
  usuario puede reabrirla; hoy no hay dato que lo pida.
- Pasar el texto de un motor a otro (OCR → VLM que corrige) solo ayudó a modelos grandes; a los chicos (≈ 7B) los empeoró.

## Comparación por etapa
| Etapa | Hoy | Lo que dicen las fuentes | Acción |
|---|---|---|---|
| Orientar | OSD de Tesseract + voto de los recortes | OpenCV: deskew + perspectiva (contorno del papel) | **Probar** (barato), medir antes/después |
| Separar | `separar(esperados)` por columnas y huecos (M-11: 42/43) | Ninguna fuente separa varios recibos de una foto; los parsers de recibo esperan uno por página | Mantener |
| Limpiar | V1 ×1,5, V2 gris, V3 recorte, V4 Real-ESRGAN | Binarizar ayuda al OCR clásico en texto degradado; sin estudio con VLM | Ya medido en T9 (V2 +0); no insistir |
| Leer | qwen2.5vl:7b (Ollama) | PaddleOCR-VL mejor F1 de campos en CORD; PP-OCRv5 ≈ 4–5 GB; TrOCR solo líneas, sin español | **Spike** PaddleOCR-VL/PP-OCRv5 en 30–50 recibos de la referencia |
| Segundo lector | Tesseract solo dígitos (R3, verifica) | docTR / Surya2 con CER parecido a Paddle | Paddle podría reemplazar a Tesseract como verificador |
| Validar | sumas, carta de precios, dígitos, nombres de foto | Los servicios de nube no validan sumas; devuelven campos con confianza | Lo nuestro va más lejos; mantener |
| Releer | ≤ 3 pasadas independientes + voto por campo | Encadenar OCR → VLM: mixto, peor en modelos chicos | Si se prueba, solo como verificador y sin mostrar los valores viejos |
| Revisar | pestaña ④ con recorte y candidatos | Azure/Google dan confianza por campo para mandar a revisión | Igual en espíritu |
| Aprender | exportar_entrenamiento (T15), LoRA fase 2 | Transkribus entrena modelos sin código (manuscritos, pago) | Fase 2 sigue con LoRA local |

## Nube (si algún día se reabre «solo local»)
Por recorte, ≈ 500 recibos/mes:
- Google Vision `DOCUMENT_TEXT_DETECTION`: 1 000 gratis/mes → 0 USD. Solo texto (nuestro parser sigue haciendo los campos).
- Document AI Expense: ≈ 0,01 USD/página (fuente secundaria) → ≈ 5 USD/mes; mejor F1 publicado en recibos torcidos (93,3 % CORD).
- Azure Read / recibo: español impreso y manuscrito; 500 gratis/mes; el recibo prearmado no trae pagado, cambio ni medio;
  los contenedores necesitan conexión para facturar (no hay modo sin internet).
- Textract AnalyzeExpense: 100 gratis, luego 10 USD/1 000; español sin confirmar.
- Privacidad: Google declara que no entrena con datos de clientes; igual las fotos salen del PC.

## Próximos pasos propuestos (fuera del plan actual; se deciden con la cifra de T16)
1. Spike: PaddleOCR-VL y PP-OCRv5 contra la referencia (`medir_precision` con otro motor), mismas 20 fotos de T9/T16.
2. Spike: OpenCV perspectiva + deskew como paso antes de `separar`; medir con `--completo`.
2b. Idea del usuario: **TrOCR solo para números** (los dígitos no dependen del idioma, así que la falta de español no pesa).
   Detector de líneas (Tesseract/Paddle) → TrOCR-printed (SROIE) por línea → montos como verificador R3 o candidato del voto
   en campos numéricos; qwen sigue con letras (medio, detalle). Base: en V0 (T9) 10 de 11 campos medidos son montos; la única
   palabra que cuenta es `medio`. Medir contra Tesseract-dígitos; costo ≈ 20–30 líneas por recibo.
2c. **Copiar el proceso de Google Vision** (docs: jerarquía página→bloque→párrafo→palabra→símbolo, cada uno con caja y
   confianza; su motor publicado: detector dedicado de texto + agrupación en líneas (Long 2022, HierText) y reconocedor por
   **línea** (Ingle 2019); tamaño de imagen, preprocesado y modelo de lenguaje no están publicados). Lo que nos falta:
   (a) leemos el recibo entero de una vez (qwen, y Tesseract-dígitos con `--psm 6` sobre todo el recorte), Google lee línea
   por línea; (b) no tenemos confianza por dígito. Réplica local: detector de líneas → cada línea de monto recortada a
   resolución nativa y agrandada → lector de línea (Tesseract LSTM con lista blanca, TrOCR o Paddle rec) con confianza por
   símbolo → monto con confianza baja va a revisión. La validación de sumas (el paso 3 que sugieren) ya la hacemos. Une 2b y 1.
   Fuentes: docs.cloud.google.com/vision/docs/fulltext-annotations · /handwriting · arXiv 1904.09150 · CVPR 2022 Long et al.
   Pasos genéricos de un pipeline HTR (otra búsqueda del usuario) vs. hoy: rotación 90° sí (OSD), deskew fino y papel curvo
   no; contraste sí (V2), nitidez solo V4; binarizar no (al VLM le puede hacer daño, pero **sí va en la ruta por línea**, para
   Tesseract/TrOCR); ROI por recibo sí (`separar`), segmentar líneas no → el hueco es el mismo de 2c.
2d. **Spike Google Vision** (usuario 2026-10-18: en las comandas solo «<NOMBRE>» es privado; reabre «solo local» para
   comparar, ADR-008 al hacerlo). Mismas 20 peores fotos (107 recibos), `DOCUMENT_TEXT_DETECTION`, sin languageHints, por
   `requests`, clave en `~/.claves/google_vision_key.txt` (o `GOOGLE_VISION_KEY`; probada 2026-10-18 con imagen
   sintética: OK). Las comandas imprimen «SU RESTAURANTE» (plantilla), no <NOMBRE>, pero sí la dirección y el teléfono reales →
   **se tapan las líneas de dirección, Teléfonos, NIT, identificación del cliente, cualquier número suelto de ≥ 7 dígitos
   sin $, los datos del domicilio (nombre y dirección del cliente) y la palabra «<NOMBRE>»** (sale también en platos: solo la
   palabra, el plato y su precio quedan); número de recibo, fecha y mesa protegidos; (cajas de Tesseract, variantes OCR tipo DAK0TA,
   pintadas en blanco a todo lo ancho; si no se hallan, la franja entre el encabezado y «RECIBO #»); antes de la primera llamada, hoja de contacto de los recortes tapados para revisar a ojo; un
   recorte donde no se encuentre el nombre pero el encabezado se vea no se envía. Si gana, **ingeniería inversa**: (a) por campo, dónde acierta y qwen falla;
   (b) sus cajas de línea vs. las nuestras (¿qué detector replicar?); (c) confianza por símbolo de sus errores (¿umbral útil
   para revisión?); (d) mismo recorte a 0,5×/1×/2× y en V2/binarizado/V4: si la salida no cambia, normaliza adentro, si
   cambia, sabemos qué tamaño y limpieza le gustan; (e) su texto de cada línea de monto contra Tesseract/TrOCR en esa caja.
3. Solo si 1–2 no cierran la brecha: relectura dirigida (imagen + motivo, sin valores viejos) o un Qwen-VL más grande.

Fuentes: cloud.google.com/vision/pricing · docs.cloud.google.com/document-ai/docs/data-usage ·
learn.microsoft.com/azure/ai-services/document-intelligence/prebuilt/receipt · aws.amazon.com/textract/pricing ·
arXiv 2210.07903 (CORD) · arXiv 2212.05525 (TrOCR SROIE) · arXiv 2008.02777 (binarizar) · arXiv 2509.17418, 2608.22366
(OCR→VLM) · paddleocr.ai PP-OCRv5 · imagetotable.ai benchmark de recibos (proveedor) · transkribus.org/pricing

## Resultado spike 2d · Google Vision vs. nuestro lector (2026-10-18)
115 recortes de las 20 peores fotos; 96 enviados tapados (19 «revisar» quedaron en el PC, entre ellos uno con cliente
con nombre y dirección: la red de seguridad sirvió). Comparables = 93 recibos de la referencia que estaban en recortes enviados.

| 93 recibos | omitidos | dudosos | validados (con error) | leídos con algún campo mal |
|---|---|---|---|---|
| V0 qwen, 1 pasada | 13 | 18 | 62 (9) | 27 |
| qwen bucle completo (T16) | 14 | 51 | 28 (3) | 23 |
| Google, texto tal cual | 16 | 39 | 38 (22) | 61 |
| Google, rearmado por filas | 16 | 10 | 67 (12) | 22 |

- **Google no lee mejor los números que qwen**: en los 71 recibos que leen los dos, los campos mal son casi iguales
  (Google 33, qwen 31); Google acierta 6 donde qwen falla y al revés 5.
- **Lo que sí copió el spike de Google es el diseño**: su texto «tal cual» pone etiquetas y montos en bloques distintos
  (61 recibos mal); rearmado por filas con sus cajas (misma altura, izquierda → derecha) baja a 22. La estructura por
  palabra con caja es lo valioso, no el motor.
- **Omite más** (16 vs. 14): en 11 de sus 16 el número de recibo ni aparece en su texto (lo lee mal o el corte lo deja fuera).
- **15 «errores» son de los dos a la vez con el mismo valor** → no son de OCR: año impreso 2025 (5; el POS tiene mal el
  reloj → regla M-10, fecha de la carpeta manda), descuento/domicilio/cortesía que la referencia guarda distinto de lo
  impreso (8), 85582/85586 con el descuento cruzado. La tasa real de error de lectura es menor que la medida.
- Conclusión: no vale pagar ni sacar fotos por Google. Siguientes pasos con más retorno: (1) aplicar M-10 a la fecha y
  revisar esos 8 casos de la referencia; (2) omitidos: el corte y la lectura del número, no el motor; (3) lector por línea
  (2c) solo para que R3 deje de dar falsas alarmas. Ingeniería inversa (d) tamaños/variantes no se corrió: Google no ganó.
