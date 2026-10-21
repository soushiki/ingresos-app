# 06 · Test report — M-25 Indra OCR · Iteración 2 (T5–T8)

## Summary
- **PASA** R2, R4 (interfaz) y R6. Diff: `4086972..HEAD` (13 archivos, +239/−25). Con `indra_venv` instalado, `motores.estado()` = `indra`, sin aviso.
- **R1/R3 (números con el bucle completo) en curso:** `medir_precision --completo --peores 20 --de-cero` en segundo plano (≈ 4 h, se puede reanudar), log en `datos/referencia/m25_completo.log`. Se compara con el informe `20261019-135040` (omitidos 5, dudosos 27, validados con error 7, 103 recibos).

## R2 por el camino de la app (20 hojas, 107 recibos; `preparar_pagina` + `separar` con `detectar=motores.detectar_giro`, lector `motores.leer_digitos`)
| ángulo | hojas derechas | incl. restante máx | números | totales | s/hoja |
|---|---|---|---|---|---|
| 0 / 90 / 180 / 270 | 18 (+2 de lado) | 0,0° | 84 | 101 | 0,16–0,20 |
| +8 | 18 (+2) | 0,9° | 85 | 101 | 0,28 |
| −25 | 18 (+2) | 0,9° | 78 | 101 | 0,35 |
| +40 | 18 (+2) | 0,9° | 79 | 101 | 0,37 |
- Las 2 «no derechas» son las hojas con recibos de lado (85524…531, 85560…565): R2 las cuenta como derechas; se leen 5/6 y 5/5 en todo ángulo. Igual que el spike (e6e46e2).
- Inclinación ≤ 1° ✓ · enderezado ≤ 0,5 s por hoja (N1) ✓ · Tesseract daba 7–14 de 20 a 90/180/270°.

## Suite
- 21 `probar_*.py` OK, 0 fallos (con el venv instalado). `probar_imagen.py` y `probar_motores_falso.py` no son suites.
- Cobertura: R2 0°/90°+8° con `detectar` falso en `probar_separar.py`; R4 aviso visto en el navegador (T7); R6 dos corridas → «Indra listo» (T8). La rama «sin py 3.14» del instalador no se pudo probar en este PC (solo revisada).

## Revisión (orientacion.py, app.py, medir_precision.py, contable.html, instalar_indra.bat)
- Sin defectos que bloqueen. El aviso usa `textContent` (sin XSS); el instalador usa `--only-binary=:all:` y requisitos fijados; el cliente fija `INDRA_OCR_MODEL_DIR` = `indra_venv\modelos` y `HF_HUB_OFFLINE=1`.
- Menor 1 (aceptado): a 0°, Indra gira 90° las 2 hojas de lado que Tesseract dejaba quietas → sus recortes ya no son idénticos a los de v1.6.0 (18/20 sí lo son). Lecturas iguales; lo decide R3 en la corrida completa.
- Menor 2 (aceptado): con −25°/+40° los números bajan a 78–79 (spike 82) por el doble remuestreo; totales intactos (101). Las fotos reales vienen casi derechas.
- Menor 3 (aceptado): con giro manual (no «auto») no se corrige la inclinación (lo eligió quien gira a mano).
- Menor 4 (aceptado): `r'%MODELOS%'` en el .bat se rompe si la carpeta tiene un apóstrofo; la ruta real es `D:\Claude\...`.
- Security-review no es obligatorio (exposed: no).

## Deuda / carga
- Sin linter en el proyecto → sin comparación; sin tarea DEBT. N1 de R3 por recorte (≤ 0,2 s) sale de la corrida completa.

## Humo manual (usuario, ≈ 5 min)
1. Arrancar la app y abrir `http://127.0.0.1:5000/api/contable/capacidades` → `"motor": "indra"`, `"aviso": null`.
2. En ① subir una foto de sept. ya conocida, girada de lado → sale derecha y con los mismos números y totales.
3. Renombrar `indra_venv` a `indra_venv_x`, reiniciar la app → banda «Indra no disponible: se usa Tesseract»; volver a llamarla `indra_venv`.
- Resultado: pendiente del usuario.
