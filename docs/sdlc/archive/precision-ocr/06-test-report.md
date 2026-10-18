# 06 · Informe de pruebas — Precisión del OCR (iteración 5: FIX-1..13 + R3b)

## Summary
- **Resultado: pasa, con 1 defecto nuevo (Should).** Las 17 suites `probar_*.py` pasan (`probar_imagen.py` es manual).
- **Cobertura:** cada FIX trae su check (probar_revision +9, probar_validar +5, probar_relectura +6, probar_precision +3,
  probar_recortes +2, probar_datos_ocr +5, probar_digitos +8). R3b cubierto (nota suave, otro número del nombre → dudoso,
  total/pagado distinto → nota). Sigue sin prueba: N4 (temperatura 0, config en `local_engine.py:24`).
- **N3 sigue sin medirse de nuevo:** la re-corrida de T16 pide re-OCR de 107 recibos con Ollama (FIX-2, pendiente en 08-maintenance).
- Diff revisado: `ed4b480..HEAD` (21 archivos, +220/−71; código ≈150 líneas).

## Fallos
- Ninguno en la suite.

## Hallazgos de la revisión (a mano, diff chico; más grave primero)
1. **FIX-14** `app.py:269` + `catalogo.py:39`: si `catalogo.json` ya trae precios, nunca se rehace. Lo que FIX-9 resetea tras
   confirmar solo vuelve a leer el mismo archivo → un precio corregido en Revisión o un día nuevo validado nunca entra a «auto».
   Hoy no se nota (el archivo está vacío, así que se arma del libro en cada lectura), pero R6 queda congelado tras su primera carga.
2. (bajo, aceptado por FIX-1) `_conservar_revisados` (`app.py:399`) vuelve a poner un «revisado» que el usuario borró a mano del día
   antes de guardar. Coherente con R7 («releer nunca pisa un revisado»); queda anotado, sin tarea.
3. (cosmético) ④ en «Revisados»: el número de la pestaña no se actualiza al corregir; se actualiza al volver a «Dudosos».
- Revisado sin hallazgos: FIX-3 (SIN_CANDIDATO), FIX-4 (sin tildes), FIX-6/7/8/10/13, colores de FIX-12, R3b `notas_digitos`/`_digitos`.

## Seguridad (`exposed: no`)
- No hay entradas nuevas: `estado=` en GET /revision ya pasaba por la lista blanca; ④ sigue armando todo con textContent (las notas ℹ también).
- `spikes/` queda fuera de lo que se publica (FIX-11). `/security-review` completo: opcional antes de 7-release.

## Carga y deuda
- Sin prueba de carga (app local de un solo usuario). No hay linter configurado, así que no hay con qué comparar la deuda.

## Smoke (para el usuario, ≈5 min)
1. ④ Revisión → selector «Revisados»: salen los confirmados con aviso verde y solo «Guardar corrección».
2. Escanear una foto de comandas con Tesseract instalado → un recibo que solo tiene «Sin confirmar por segundo lector» muestra ℹ y NO cuenta como dudoso.
3. Un recibo a domicilio / para llevar ya no pide «Falta la mesa».
4. Exportar el Excel: dudoso en naranja, otros avisos en amarillo; un revisado sin «Motivo».
Resultado: pendiente del usuario.
