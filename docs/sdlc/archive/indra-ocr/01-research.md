# 01 · Investigación — M-25 Indra OCR (ligera)

Base: spike `docs/ocr-indra-comparison.md` (e6e46e2). Aquí solo lo que el spike no cubría.

## Summary
- **El trabajador aparte sigue siendo obligatorio:** onnxruntime 1.31.0 (9-oct-2026) solo publica ruedas Windows cp311–cp314, ninguna cp315. Indra corre en su venv 3.14 y la app (3.15) le habla por tubería.
- **Protocolo: JSON por líneas en stdin/stdout, como `spikes/indra_ocr/indra_worker.py`.** Se agregan: saludo `ready` con tiempo límite de arranque, tiempo límite por pedido con matar y reiniciar, stderr drenado a un log, un candado alrededor de cada pedido/respuesta, cierre con `quit` → `wait` → `kill` y `atexit`, y `CREATE_NO_WINDOW`.
- **Fijar `indra-ocr==1.1.2`** (última, 20-oct-2026). La carpeta de modelos va en `INDRA_OCR_MODEL_DIR`. `upright()` funciona en 1.1.2 (el spike lo usó), pero no está documentado: es una API frágil, y la versión fijada más una prueba la protegen.
- **Enganches en la app:** R3 cambia el callable `leer_digitos` (`app.py:292`, hoy `digitos.numeros_tesseract`). La orientación cambia `giro_automatico` (`orientacion.py:19`), usado por `preparar_pagina` y `_recortes`. Las reglas de `validar.py` no cambian.
- **Licencia:** el código es Apache-2.0. Los pesos son OpenRAIL-M modificada: gratis bajo US$20 M y sin competir con la API de Datalab, así que aplica. No redistribuimos los pesos: el instalador los descarga una vez en cada PC.

## Options compared
| Pregunta | Opción | Encaje | Costo | Madurez | Veredicto |
|---|---|---|---|---|---|
| Cómo correr Indra | Trabajador persistente en venv 3.14, JSON por líneas | Ya probado en el spike; ≈ 0,9 s de carga una sola vez | Bajo | Patrón estándar de subprocess | **Elegida** |
| | Lanzar un proceso por foto | Simple | +0,9 s de carga por foto | – | No |
| | Pasar la app a 3.14 | Quita la tubería | Rehacer el entorno de todos los PC | – | No |
| | Esperar ruedas cp315 | Cero trabajo | Sin fecha | – | No; volver a mirar en 08 |
| Concurrencia | Un candado y un solo trabajador; `intra_op` = núcleos físicos (4), `inter_op` = 1 | Flask atiende hilos y la carga es baja | – | – | **Elegida** |
| Modelos | Descarga única con `INDRA_OCR_MODEL_DIR`, luego sin red | Cumple «offline» | 76 MB por PC | 1.1.0 dejó de revisar a diario y conserva la caché si falla | **Elegida**; verificar que sin red no hay ningún intento de conexión |
| Si falta Indra | Volver a Tesseract (v1.6.0) y avisar | Igual que hoy cuando falta Tesseract (`digitos.py:28-32`) | – | – | **Elegida** (meta) |

## Codebase map
- R3: `ocr_module/digitos.py:10` `_enteros` y `:20` `numeros_tesseract`; sin Tesseract → `None` y un aviso. Se llama por pasada en `relectura.py:76,96-97`.
- Notas: `validar.py:138` «Sin confirmar por segundo lector» (nota suave). Regla de dudoso en `:141-147`, llamada en `:178,193`.
- Orientación: `orientacion.py:8` `CONFIANZA_MIN=0.8`, `:11-16` busca Tesseract, `:19` `giro_automatico`, `:47-57` `preparar_pagina`, `:32` `recortar`, `:185` `separar`, `:233-243` `_recortes` (gira papeles de lado).
- R5: `validar.py:43-52` `leer_nombre`, `relectura.py:141-155,191-203` cercanía, `faltantes.py:16` «Falta el recibo N».
- Capacidades en la interfaz: `app.py:252-254` `/api/contable/capacidades`. Arranque: `iniciar.bat` → `python app.py`, puerto 5050, en 127.0.0.1.
- Pruebas: `python probar_<x>.py`, sin pytest. Tocan esto `probar_digitos` (16), `probar_validar` (56), `probar_relectura` (76), `probar_separar` (14), `probar_faltantes` (19), `probar_precision`.
- Base del cliente: `spikes/indra_ocr/indra_worker.py:26-44` y `indra_cliente.py:9-39` (`INDRA_VENV`).

## Risks / unknowns
1. **El salto del 8→6 en el número del recibo da 3 dudosos falsos por cada ≈ 100.** Van a ④, no se pierden. ¿Conviene suavizar la regla `validar.py:141-147` solo con Indra? Lo decide requisitos.
2. **La meta «omitidos 5 → ≤ 2/103» no está medida.** El spike midió R3 (confirmaciones), no los omitidos con el bucle completo de qwen. Hay que medirlos en 6-test con `medir_precision` y el set congelado.
3. **`upright()` no está documentado y el repo de Indra tiene semanas de vida y un solo mantenedor.** Mitigación: versión fijada, una prueba de humo del trabajador y el respaldo a Tesseract.
4. **Windows no aparece como probado oficialmente,** aunque corrió bien en el spike. El instalador necesita que esté `py -3.14`: falta definir qué hace si no está.
5. **El recargador de Werkzeug** puede lanzar dos trabajadores. Hay que arrancarlo de forma perezosa en el primer uso, no al importar.
6. **Si Flask muere, el trabajador puede quedar huérfano** (440 MB). Solución: un Job Object de Windows o que el trabajador se cierre al recibir EOF en stdin.
7. **Licencia:** no se pudo leer el texto completo de la tarjeta del modelo (HF devolvió 401). Hay que leerlo una vez antes de publicar.
8. **Enderezado con fotos reales sobre la mesa** (perspectiva y fondo) no está probado. Solo se probaron giros sintéticos.

## Sources
- https://pypi.org/project/onnxruntime/#files
- https://pypi.org/pypi/indra-ocr/json
- https://github.com/datalab-to/indra/blob/main/CHANGELOG.md
- https://github.com/datalab-to/indra/blob/main/README.md
- https://docs.python.org/3/library/subprocess.html
- https://onnxruntime.ai/docs/performance/tune-performance/threading.html
- https://flask.palletsprojects.com/en/stable/server/
