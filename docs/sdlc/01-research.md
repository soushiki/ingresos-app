# 01 · Research — M-13 recibos omitidos (2026-10-18)

## Summary
- De los 13 omitidos de M-12, **solo 3 son del corte**: 85340 y 85343 (la foto «3/85334-338 al 3341-343» no se separa: el nombre
  no se entiende → `esperados` = None → 1 sola pieza) y 85588 (13/85582: una columna con 3 papeles junta 2, ya en M-11).
- **Los otros 10 salen bien cortados** (separar corrido de nuevo en las 9 fotos: 6/6 piezas, un papel por pieza, «RECIBO #» visible).
  Se pierden **después del corte**: el número no se lee (las piezas de 5/85387 miden ≈ 250 px de ancho, el número es diminuto) o la pieza
  sale con otro `tipo`. `medir` solo cuenta `tipo=="venta"` (`referencia.py:85-90`) y el informe no guarda nada por pieza.
- **«Falta N» a mano en ④ es lo más barato (S)**: R5 ya da el aviso (`validar.py:76-79`) y ④ ya tiene un formulario de documento manual
  (`contable.html:192` `nuevoDoc`, `origen:"manual"`). Falta un botón que cree la fila del número que falta, con la foto al lado.
- El lector por línea (Tesseract con cajas de palabras, 01d-2c) no existe en la app (`image_to_data` solo está en el spike) → M.
- Recomendación: (1) «falta N» en ④; (2) entender mejor el nombre de la foto (arregla 2 de los 13 sin tocar el OCR); (3) un registro por pieza
  en `medir` para saber si los 10 son número o tipo; solo entonces decidir el lector del número (recortar arriba y ampliar, o leer por línea).

## Options compared
| Opción | Qué cubre de los 13 | Costo | Madurez | Veredicto |
|---|---|---|---|---|
| «Falta N» a mano en ④ (R5 + formulario manual) | los 13 (y los futuros), con trabajo a mano | S | aviso y formulario ya existen | **sí, primero** |
| Entender el nombre «85334-338 al 3341-343» | 2 (85340, 85343) | XS–S | `numeros_de_nombre` (`validar.py:35`) | **sí** |
| Registro por pieza en `medir` (número, tipo, texto) | 0 directos; dice la causa de los 10 | XS | — | **sí, antes de leer mejor** |
| Número de la cabecera: recortar arriba y ampliar (V4/×2) + dígitos | probablemente la mayoría de los 10 | S | V4 y `digitos.py` ya existen | después del registro |
| Lector por línea (Tesseract `image_to_data`, rearmar por filas) | los 10, en teoría | M | sin código (solo el spike) | si el anterior no alcanza |
| Mejor separador (columna con 3 papeles) | 1 (85588) | S | M-11, quedan 6 fotos | después; poco rinde |

## Codebase map
- Entrada: `iniciar.bat` → `python app.py` (Flask 127.0.0.1); `/api/contable/escanear` `app.py:291`, revisión `app.py:408-449`.
- `ocr_module/`: `orientacion.separar` (`:185`, `_por_columnas` `:154`), `tesseract_engine`, `digitos`, `preprocess` (V1–V4).
- `parser_module/contable/`: `documentos.py:108` (número del recibo), `relectura.py` (R3/R5/R6), `validar.py` (R5 `faltantes`),
  `referencia.py` (omitidos), `recortes.py`.
- ④ Revisión: `static/contable.html` (avisos `:222,247,258`); libro en `datos/libro.json` (`POST /api/contable/libro`, `app.py:364`).
- Pruebas: `python probar_<x>.py` (separar, validar, relectura, contable…); medir: `python medir_precision.py --completo`.

## Risks / unknowns
- **Los 10 cortados bien: número o tipo, sin saber.** El informe M-12 no guarda nada por pieza; hay que volver a correr las 9 fotos
  con registro (≈ 10 fotos × qwen; minutos, no horas).
- La meta ≤ 2 % (≤ 2 de 107) cuenta solo lo que lee el OCR; «falta N» cierra el hueco a mano pero no baja el número medido. En requisitos:
  ¿los anotados a mano cuentan como no omitidos?
- La resolución de las piezas (≈ 250 px de ancho en 5/85387) puede ser el techo: si la foto es lejana, ningún lector local lee el número.
- Nombres de foto con errores de digitación («3341» por 85341): ¿adivinar o avisar «no entiendo el nombre»?
- Para ver los recortes del diagnóstico hay hojas de contacto en la carpeta temporal de la sesión (no se guardan en el repo).

## Sources
- `datos/referencia/informes/20261018-120343_completo.json` (M-12), `docs/sdlc/08-maintenance.md` M-11/M-12/M-13, `docs/sdlc/01d-fuentes-ocr.md` 2c/2d
- `separar` vuelto a correr el 2026-10-18 sobre las 9 fotos de `data/SEPTIEMBRE` (script en la carpeta temporal, sin OCR)
