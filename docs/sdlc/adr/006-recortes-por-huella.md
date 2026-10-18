# ADR-006 · Los recortes se guardan en disco por huella, fuera del libro

Estado: aceptado (2026-10-18, aprobado por el usuario)

## Contexto
La revisión (R8) y la fase 2 (R10) necesitan la imagen de cada recibo. Hoy los recortes viven solo en memoria y se pierden. N5 pide no duplicar fotos enteras y poder borrar. ADR-004 deja las fotos fuera del .json crudo.

## Opciones
1. Guardar el recorte en base64 dentro de `libro.json`: un solo archivo, pero el libro crece ~80 kB por recibo (~0,5 GB/año) y el .json crudo también.
2. Guardar solo la ruta de la foto + coordenadas del recorte: no duplica nada, pero si la foto se mueve o borra, la revisión queda ciega, y hay que recortar de nuevo al mostrar.
3. **Guardar cada recorte como JPEG gris en `datos/recortes/<sha256[:16]>.jpg`** y en el documento solo el nombre.

## Decisión
Opción 3. Solo `recortes.py` escribe y borra en esa carpeta; la ruta HTTP sirve solo nombres que cumplen `^[0-9a-f]{16}\.jpg$`. La huella hace que releer la misma foto no duplique archivos. El recorte no viaja en el .json crudo (como las fotos en ADR-004).

## Consecuencias
+ Libro y .json crudo siguen livianos. + Borrar por fechas y limpiar huérfanos es posible (N5).
− En el PC del contador la revisión muestra «sin recorte» (allí no se lee OCR).
− Respaldar `datos/` incluye `recortes/` (anotarlo en 07-release).

## Fitness test (`probar_precision.py`)
- Ningún documento de `libro.json` ni del .json crudo exportado tiene un valor que empiece por `data:image` o pase de 20.000 caracteres. Mensaje: «ADR-006: imagen dentro del libro».
- `GET /api/contable/recorte/..%2Flibro.json` da 404. Mensaje: «ADR-006: la ruta de recortes sale de su carpeta».
