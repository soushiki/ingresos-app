# 06 · Test report — Iteración 4, re-test (FIX-13, FIX-14)

## Summary
- **Resultado: pasa.** FIX-13 y FIX-14 están cerrados, cada uno con su check. La suite completa está verde y la revisión no encontró defectos nuevos. Con esto pasan las 4 iteraciones; queda 7-release.
- Cobertura de la it. 4 (sin R-ids nuevos; criterios = «done when» de T18–T21 y 03 §10):
  - T18–T21: cubiertos como en el test anterior (ida y vuelta, rechazos de archivo, 8 clases de día malo, iguales/conflicto/reemplazar/bloqueado R7, subproceso SIN_OCR → CTG-1).
  - FIX-13: un cierre con faltante (`faltante_impreso` y `cierre.faltante` negativos) sale por `crudo`, pasa `leer_crudo`, se importa por POST y queda igual en el libro. El caso de tope del test es ahora 10^11.
  - FIX-14: un texto de 6.000 caracteres entra. Un JSON anidado 100.000 niveles da `CrudoInvalido`, el POST responde 400 y no escribe nada (antes daba 500).

## Failures (suite completa, 2026-10-17)
- Ninguna. Verdes: probar_contable, probar_datos_ocr, probar_dia15, probar_documento_soporte, probar_esquema, probar_parser (79/79), probar_pdf y probar_restaurante. probar_imagen es una herramienta manual que pide una imagen; no es parte de la suite.

## Comprobación con datos reales
- Los 30 días reales de septiembre: `crudo → leer_crudo` da 30 válidos y 0 inválidos.
- El día real 2026-09-16, con un faltante de −3.000 puesto en sus 5 cierres, se valida y vuelve igual. Ese es el caso que fallaba en el test anterior.

## Review findings (diff ebf9702..HEAD: exportar.py +5/−4, probar_datos_ocr.py +17, ADR-004)
- `_malo` acepta |v| ≤ 10^10. NaN sigue rechazado (`v == v`). bool y None siguen aparte.
- Que entren negativos no abre camino a un DS negativo: `soporte.compras` salta las compras con valor ≤ 0 (soporte.py:129) y `generar` las rechaza (soporte.py:229).
- `RecursionError` se captura junto a `ValueError`. La validación de forma sigue completa antes de escribir y bajo `LOCK`.
- MAX_TEXTO = 20.000 deja ~5× de margen sobre el texto real más largo (4.038). MAX_DOCS (2.000) limita el tamaño del archivo.
- ADR-004 anota los dos topes y el porqué.
- Menor (8-maintain, ya anotado): un archivo hecho a mano con una factura de valor negativo entraría al libro contable como cifra negativa. El soporte la ignora. Es el mismo riesgo que editar libro.json a mano. Sigue abierto el otro menor: `id` repetidos dentro de un día.
- `/security-review` a mano (entrada de otro equipo): sin hallazgos nuevos.

## Debt
- Sin linter. +9 líneas de código, sin funciones nuevas. Sin DEBT nuevo.

## Smoke (usuario, ≈5 min, sigue pendiente)
1. En tu PC (con Ollama): ② Libro contable → filtra una semana → «Datos crudos (.json)».
2. En la copia del contador (`.env` con SIN_OCR=1, `iniciar.bat`): el chip dice «Sin OCR · importa datos» y ① muestra «Importar datos».
3. ② → «⬆ Importar datos crudos» → elige el .json: el informe muestra N nuevos. Si importas el mismo archivo otra vez, todos salen como «iguales».
4. ③: aparecen las mismas semanas que en tu PC. Genera un CTG y baja su Excel.
5. En una ventana de 375 px, ① y ② no tienen scroll lateral.
- Siguen pendientes los smokes de las it. 1 (abrir el Excel con fórmulas), 2 y 3. Conviene hacerlos antes de 7-release.
