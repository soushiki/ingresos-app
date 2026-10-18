# ADR-005 · Validar cada recibo y releer solo lo dudoso, en el servidor

Estado: aceptado (2026-10-18, aprobado por el usuario)

## Contexto
≈40 % de los recibos de septiembre necesitó corrección. Con temperatura 0, leer dos veces la misma imagen da lo mismo (01-research), así que la segunda opinión tiene que venir de otra imagen o de otro motor. N2 acepta hasta ~3× el tiempo por foto; N1 prohíbe motores en la nube.

## Opciones
1. **Leer siempre N variantes y votar**: simple, pero gasta 3–4× en todos los recibos, también en el 60 % que ya sale bien.
2. **Consenso entre varios VLM (CE-OCR)**: buena evidencia, pero exige otro modelo local en memoria y duplica el tiempo base.
3. **Leer una vez, validar con la aritmética del recibo y releer con variantes de imagen solo lo que no valida** (máx. 3), con Tesseract como segundo lector de dígitos.

## Decisión
Opción 3, en `relectura.leer_recibo` llamado desde `_leer_hoja` (servidor), no desde el navegador: el bucle necesita el recorte y el motor, y así el navegador sigue mandando una foto por vez. `validar()` es pura (sin E/S) para poder probarla sin Ollama. Si un candidato completo valida, gana entero; si no, voto por campo y el recibo queda «dudoso» con el valor más probable (R7). Una foto borrosa (R4) siempre lleva una segunda variante, aunque valide.

## Consecuencias
+ El costo extra cae solo en los dudosos (≈2,2× de media). + Cada valor guarda variante, pasada y motor (N4).
− Hay que ampliar `parse_venta` (ítems, subtotal, pagado, cambio, hora) para que la aritmética exista.
− Tope por foto: al agotarlo, lo pendiente queda «dudoso: tiempo agotado».

## Fitness test (`probar_precision.py`, motor simulado que cuenta llamadas)
- Un recibo que valida a la primera se lee exactamente una vez. Mensaje: «ADR-005: recibo válido releído».
- Un recibo dudoso se lee como máximo 1 + max_relecturas veces. Mensaje: «ADR-005: relecturas sin tope».
- `validar.py` no importa `requests`, `ocr_module` ni abre archivos. Mensaje: «ADR-005: validar() dejó de ser pura».
