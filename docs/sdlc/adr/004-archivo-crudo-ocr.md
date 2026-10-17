# ADR-004 · Los datos crudos viajan en un .json versionado, sin fotos, día por día

Estado: aceptado (2026-10-17, aprobado por el usuario en D1)

## Contexto
El PC del contador no corre Ollama. La lectura OCR se hace en otro PC y el libro y los documentos soporte se arman en el del contador. La frontera ya existe: cada día de `libro.json` guarda `documentos` (papeles leídos), `banco` y `cierre`; `filas`, `cruces`, `debito` y `credito` se derivan con `construir_asientos` (ADR-002). Un documento tiene campos anidados (`datos` dict, `avisos` y `gastos_detalle` listas) y `texto` de hasta ~4.000 caracteres con saltos de línea.

## Opciones
1. **.xlsx con la hoja DATOS OCR + versión**: se puede abrir, pero DATOS OCR es derivada (una fila por papel y medio) y no permite volver a armar los documentos. Para no perder campos habría que meter JSON en celdas, y Excel convierte en silencio números como «00123» y las fechas.
2. CSV: Excel en español usa «;» y coma decimal; además tiene el mismo problema de campos anidados.
3. **.json con `formato`, `version` y `sha256`**: sin pérdida, lo escribe y lo lee la librería estándar, y la huella detecta si el archivo se cortó o se editó a mano.

## Decisión
Opción 3. Archivo `ingresos_crudo_<desde>_<hasta>.json` = `{formato: "ingresos-crudo", version: 1, exportado, desde, hasta, sha256, dias: [{fecha, documentos, banco, cierre, guardado}]}`. Solo viaja lo que se leyó; lo derivado se recalcula al importar con la config del contador (un solo cálculo, ADR-002). Las **fotos no viajan**: `origen` ya guarda la ruta del papel. Para revisar a ojo está el Excel del libro (DATOS OCR).
Importar, día por día: si el día es nuevo, se agrega. Si ya existe y es igual, se omite. Si ya existe y es distinto, **no se toca** y se lista como conflicto; el usuario puede marcarlo para «reemplazar». Si el día tiene compras de un DS transmitido, nunca se reemplaza (R7, `bloqueos()`). No se fusionan días, porque mezclar papeles por id duplica compras. Un día con un documento inválido no entra y sale en el informe con el motivo (R10: nada se pierde en silencio). Topes por valor: números con |v| ≤ 10^10 (negativos sí: el cierre guarda el faltante como `faltante_impreso` < 0; FIX-13), textos ≤ 20.000 (el OCR real ya llega a ~4.000; FIX-14). Un JSON demasiado anidado (RecursionError) es archivo inválido: 400 sin escribir.

## Consecuencias
+ Ida y vuelta exacta: los mismos documentos dan las mismas filas y las mismas semanas. − El archivo no es para editarlo a mano: las correcciones se hacen en la app después de importar.
− Las reclasificaciones que el contador «aprende» se quedan en su `clasificacion.json`. Una nueva importación trae la `cuenta` que se exportó.

## Fitness test (`probar_datos_ocr.py`)
- Exportar → importar en un libro vacío da `documentos` y `filas` iguales día por día. Mensaje: «ADR-004: la ida y vuelta perdió datos».
- Un archivo con `version` ≠ 1 o con una `sha256` que no coincide se rechaza sin escribir nada. Mensaje: «ADR-004: archivo ajeno aceptado».
