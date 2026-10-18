# 01 · Investigación — Precisión del OCR (2026-10-17)

## Summary
- El error de hoy es grande: de ~578 ventas de septiembre, el OCR **omitió 96 recibos (≈17 %)**, erró el medio de pago en 49, los montos en 48 y el número en 25, y dejó 28 papeles basura o repetidos. En total, ≈40 % de los recibos necesitó corrección a mano.
- Tipos de error vistos (en orden de peso): recibos pegados en un bloque (M-9), recibos de una foto que no se leen, montos o medio cruzados entre recibos vecinos, dígitos mal leídos (6↔8, números cortados), línea de pago perdida, papel equivocado (orden de consumo, gasto leído como venta) y fecha impresa mal leída.
- La literatura no tiene cifras para Qwen2.5-VL con recibos: **hay que medir con nuestros datos**. Los ~227 recibos corregidos este mes son el conjunto de referencia (ground truth).
- Lo que más rinde, según la evidencia y nuestros datos: **validar cada recibo con su propia aritmética** y con reglas del negocio, y **releer** (con variantes de imagen) solo lo que falla. Lo que no pasa va a revisión con la foto.
- Usar el **tiempo del OCR** como señal de foto borrosa es débil: depende de cuánto texto escribe el modelo. La medida estándar es la **varianza del Laplaciano** (más Tenengrad para desempatar). Se medirán las dos contra el ground truth.
- Con temperatura 0, leer dos veces la misma imagen da lo mismo. La variación tiene que venir de **variantes de imagen** (resolución, contraste, recorte) o de **otro motor** (Tesseract solo para dígitos).
- **Binarizar puede empeorar** a un VLM (estudio con Qwen2.5-VL-7B: binarizar y quitar ruido bajó la precisión; enfocar ayudó en un caso). Por defecto, color o gris, sin binarizar; probarlo A/B.
- Ventaja del negocio: la **carta tiene precios fijos** (p. ej. Combo Amor y Amistad 55.000, Smoky Burger 30.000). Un catálogo producto→precio permite validar ítems y **predecir** el valor de una línea mal impresa sin entrenar nada.
- A futuro (pedido del usuario): **afinar (LoRA) un modelo de visión** con nuestros recibos corregidos, para que «aprenda» este formato. Hay antecedentes (Receipt-Bench 2026 con Qwen3-VL-4B afinado; LoRA de Qwen2.5-VL-3B para recibos con 58,9 % de coincidencia exacta de todos los campos, cifra preliminar). Requiere más datos etiquetados (cientos de recibos) y GPU; queda como fase 2.

## Hallazgos (fuentes)
1. **Consenso entre modelos**, CE-OCR (arXiv 2504.11101): varios VLM votan; si la «entropía de consenso» es baja se acepta, si es alta se escala. La ganancia reportada varía entre fuentes (15–42 % F1).
2. **Predecir errores** del VLM con sondas (arXiv 2511.19806): sirve para abstenerse, pero el estudio es de texto en escena, no de recibos.
3. **Receipt-Bench** (arXiv 2605.22413): los modelos chicos afinados sobre todo omiten campos y leen mal dígitos. Los grandes **inventan valores plausibles**, que pueden hacer cuadrar un total falso. Por eso no basta con que la suma cierre: además se exige que el valor aparezca en el texto leído.
4. **Validación aritmética** (informes de práctica): atrapa errores de total. Necesita una tolerancia de redondeo.
5. **Resolución**: Qwen2.5-VL usa bloques de 28×28 px. Un min_pixels demasiado alto también empeora. Regla tipo Tesseract: altura de letra ≥20 px (ideal 20–40). Hay que verificar cómo Ollama reduce la imagen.
6. **Foto**: plana, de frente, sin flash (brillo), con el recibo llenando el cuadro; corregir la perspectiva por recibo. CLAHE (clip ≈2) solo si hay poco contraste.
7. **Votación ROVER** (multi-motor): viene del habla. En OCR solo hay tesis que muestran poca correlación de errores entre motores, sin una cifra limpia de mejora.

## Opciones para el diseño (a decidir en requisitos)
| Pieza | Qué hace | Costo | Evidencia |
|---|---|---|---|
| A. Validación por recibo | Aritmética (ítems = subtotal; subtotal − descuento + domicilio = total; total + propina = pagado; pagado − cambio = efectivo), número dentro del rango del archivo y en orden con la hora, un membrete por recorte, catálogo de precios | Bajo | Alta (nuestros datos) |
| B. Relectura con variantes + voto por campo | 2–3 variantes (tamaño, contraste, recorte), gana el candidato que valida | Medio (×2–3 tiempo) | Media, hay que medir |
| C. Tesseract solo para dígitos | Cruce independiente de números | Bajo | Media |
| D. Medidor de foto borrosa | Varianza del Laplaciano (umbral inicial ~100, a calibrar) + tiempo como señal secundaria → más pasadas | Bajo | Media |
| E. Cola de revisión con foto | Lo que no valida tras N pasadas | Medio | Alta (lo hicimos a mano) |
| F. Métrica de precisión | Conjunto de referencia de este mes; precisión por campo antes/después de cada cambio | Bajo | Necesaria |
| G. Modelo afinado (fase 2) | LoRA con nuestros recibos | Alto | Media |

## Riesgos
- Más tiempo por foto (aceptado por el usuario: menos errores importa más que la velocidad).
- Los umbrales (Laplaciano, tolerancias) sin calibrar pueden marcar demasiadas fotos o muy pocas → calibrar con el ground truth.
- Un modelo que «predice» valores puede inventar: toda predicción queda marcada como tal y nunca reemplaza en silencio un valor leído.
