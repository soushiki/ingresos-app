# 01 · Research — M-27 cuenta PUC por origen e ítem (ligera, 2026-10-25)

## Summary
- **Clasificador:** no agregar dependencias. Capas en este orden: origen → enseñado → frases/léxico a mano → léxico minado del manual (palabra→cuenta, ≥ 2 veces, ≥ 80 %, sale del cuadro) → vecino más parecido del manual (difflib de la stdlib o n-gramas de caracteres en Python puro, para errores como «domcilios» o «recuados») → cuenta puente si la confianza es baja o hay empate. Cada capa da un motivo («parecido a Julio fila 631»).
- **sklearn/rapidfuzz** quedan como plan B solo si la medición sale bajo la meta: no están instalados, y el `requirements.txt` está fijado y auditado (pip-audit) en varios PC.
- **Medición:** validar agrupando por mes (entrenar con jun–ago, probar con sept–oct). Así un texto casi repetido no aparece en las dos partes. Una meta de acierto por ítem va en requirements.
- **Código hoy:** una sola `cuenta` por documento (`documentos.py:91`), y los ítems (solo en venta/Rappi) no tienen cuenta. `asientos.construir` arma 1 débito y 1 crédito por documento (`asientos.py:452`). No existe el campo «origen». Ningún proceso reclasifica días guardados. Todo esto cambia en el ciclo.
- **PUC:** las clases, grupos, cuentas y subcuentas (6 dígitos) del Decreto 2650 mantienen su nombre oficial. Las auxiliares (desde el 7.º dígito) las nombra el negocio. Las fuentes no se ponen de acuerdo sobre la vigencia del PUC tras NIIF para una persona natural, y no hay fuentes para 1405 vs 1435, domicilios ni Rappi, así que esos puntos siguen siendo del contador (regla de mayoría, «por confirmar»).

## Options compared
| Pregunta | Opción | Encaje | Costo | Madurez | Veredicto |
|---|---|---|---|---|---|
| Q1 | a. Léxico a mano (hoy) | explicable, no tolera errores | upkeep manual | hledger-style | **se queda** como capa 1 |
| Q1 | b. Léxico minado del cuadro | explicable, barato | nulo (ya existe hoja PALABRAS) | ad hoc | **sí**, capa 2 |
| Q1 | c. Vecino más parecido (difflib / n-gramas propios) | da «por qué» con fila del manual; tolera errores | ~50 líneas, sin deps | stdlib | **sí**, capa 3 |
| Q1 | d. TF-IDF char_wb + LR/SVC (sklearn) | mejor con errores y palabras nuevas | +scipy/sklearn, auditoría, instalar en cada PC | maduro | plan B si falla la meta |
| Q1 | rapidfuzz | igual que c, más rápido | +1 dep (MIT) | maduro | no hace falta con ~1.5k filas |
| Q2 | Auxiliares de 8 dígitos bajo subcuenta oficial, validadas con `puc_cuentas.json` | sigue el Art. 6–7 del D. 2650 | ya existe `puc.py` | decreto 1993 | **sí** |
| Q2 | Taxonomía propia NIIF sin códigos PUC | según siemprealdia | rehacer export y manual | 2023 | no: el manual y el contador usan PUC |
| Q2 | Un asiento con varios débitos (por ítem) y un crédito | partida doble normal (razonado, sin fuente) | cambia `asientos.py` | estándar | **sí**, confirmar con el contador |

## Codebase map
- Clasificador: `parser_module/contable/clasificar.py` (77 líneas). Las capas hoy son: enseñado → `terceros_cuentas.json` → FRASES → LEXICO. Lo aprendido se guarda en `clasificacion.json` {terceros, detalles}.
- Llamadas: `app.py:216-222` `_clasificar` (solo llena la cuenta si está vacía; pasa tercero solo en `factura`), `app.py:337/351/358` usan `_clasificar`, `app.py:366` aprende, `app.py:965` también clasifica.
- Documento: `_base` en `documentos.py:91-92` (cuenta, conf, motivo, tercero, medio, valor, origen). `_items` en `documentos.py:113-120` (cant, nombre, valor). Los tipos están en `documentos.py:307`: venta (Rappi = venta+rappi), cierre, gasto_caja, caja_menor_manuscrito, factura, faltante, otro.
- Asientos: `asientos.py:288` construir. Puentes en `asientos.py:22`: gasto 51959501 e ingreso 13809501 (se cambian en `contable.json`). La cola `pendientes` está en `asientos.py:447/471`.
- Extracto: las líneas traen origen (regla/recordada/manual/factura) y destino (`extracto.py:156-186`). Las que tienen `revisar` van a la puente; endpoint en `app.py:418`.
- Recalcular: `_recalcular_dia` (`app.py:409`) solo rehace el extracto. El export y el import (`app.py:770-812`) usan la `cuenta` guardada.
- PUC: `puc.py` busca nombres y valida contra `puc_cuentas.json`. Insumos del ciclo: `../data/cuadro_clasificacion_puc.xlsx` (hojas CUADRO 46, PALABRAS 79, DIFERENCIAS CON LA APP 32) y `../data/inconsistencias_clasificacion_puc.pdf`.
- Tests: `py probar_contable.py` (clasificación), `probar_dia15.py`, `probar_extracto.py`, `probar_datos_ocr.py`. No hay pytest.

## Risks / unknowns
- R1 Hoy los ítems con valor solo existen en venta/Rappi. Para repartir una factura o un gasto por ítem, el OCR debe sacar ítems con valor en esos papeles. ¿Lo hace hoy? Medir antes de diseñar.
- R2 Si los ítems no suman el total del papel (OCR, propina, descuento), ¿a qué cuenta va la diferencia? ¿A la puente?
- R3 Recalcular días guardados puede pisar cuentas que el usuario corrigió a mano. Hay que marcar «manual» y no tocarlas.
- R4 El manual es inconsistente (11 ítems con varias cuentas, 9 proveedores, 4 códigos que no existen, 6 nombres distintos). La regla de mayoría aprende esos errores hasta que conteste el contador.
- R5 Desbalance de clases: 41401501 y 11200501 dominan. Hay que medir el acierto por cuenta, no solo el global.
- R6 El cuadro vive fuera de la app (`../data/`). Hay que decidir si se copia un extracto versionado, sin datos personales, dentro de `parser_module/contable/`.
- R7 (regulated) El export cambia de un renglón a varios por papel. Hay que avisar al contador y al formato «BALANCE x CTA».

## Sources
- https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html
- https://github.com/beancount/smart_importer
- https://rapidfuzz.github.io/RapidFuzz/
- https://hledger.org/manual.html
- https://gestornormativo.creg.gov.co/gestor/entorno/docs/decreto_2650_1993.htm
- https://actualicese.com/plan-unico-de-cuentas/
- https://siemprealdia.co/colombia/contabilidad/puc-bajo-niif-para-pymes/
- https://www.gerencie.com/empresas-que-deben-aplicar-las-niif.html
