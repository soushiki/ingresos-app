# 06 · Informe de pruebas — Precisión del OCR (iteraciones 1–4, T1–T16)

## Summary
- **Resultado: pasa con defectos.** Las 17 suites `probar_*.py` pasan (`probar_imagen.py` es una herramienta manual que pide una imagen).
- **Cobertura de R-ids:** R1, R2, R4, R5, R7, R8, R9, R10 tienen pruebas para cada Dado/Cuando/Entonces (validar, relectura, separar,
  revision, datos_ocr, precision, entrenamiento, recortes). R3 y R6 también (digitos, validar). Sin prueba: N4 (temperatura 0: es config en
  `local_engine.py:24`) y el cambio de R3 del 2026-10-18 (nota suave), que aún no está implementado.
- **N3 no se cumple** (T16: omitidos 16,8 %, validados con error 3,4 %). Ya está en 08-maintenance; FIX-1/2/4/5 tocan sus causas.
- Diff revisado: `4dad726..HEAD` (27 archivos, +2158/−32).

## Fallos
- Ninguno en la suite.

## Hallazgos de la revisión (`/code-review high`; más grave primero) → FIX-1..FIX-10 en 04-plan
1. `app.py:382` re-leer un día descarta un «revisado» que la nueva lectura no trae (y puede duplicarlo). Rompe R7.
2. `medir_precision.py:83` en --completo, un recibo «validado» con aviso «Foto borrosa» cuenta como dudoso → cifras N3 sesgadas.
3. `relectura.py:88` si el voto valida, igual queda «dudoso» con los motivos de V0, que no son los del documento guardado.
4. `validar.py:125` domicilio / para llevar siempre tienen «Falta la mesa» → falsas alarmas y relecturas inútiles.
5. `validar.py:14` `regla_items` encendida por defecto aunque T2 midió que cuadra solo en el 72 % de los recibos.
6. `app.py:428` editar `fecha` en Revisión no mueve el recibo de día; la referencia lo archiva en otro mes.
7. `recortes.py:17` un recorte reutilizado conserva el mtime viejo → borrar por fechas borra uno que sí se usa.
8. `medir_precision.py:79` --completo no pasa `completa=False` en PDF de varias páginas → «Falta el recibo» falso.
9. `app.py:266` con el catálogo vacío se lee el libro entero y se reescribe catalogo.json en cada escaneo.
10. `referencia.py:48` un recibo sin número se duplica en la referencia cada vez que se confirma.

## Seguridad (repaso a mano; `exposed: no`, pero toca entradas)
- `POST /revision`: fecha/id con regex, lista blanca de campos y tipos, tope 64 KB → bien. `GET /recorte/<nombre>`: solo `^[0-9a-f]{16}\.jpg$` → bien.
- `superres`: ejecutable fijo, lista de argumentos sin shell, carpeta temporal → bien. Revisión en la UI usa textContent → sin XSS.
- **N1:** `spike_google_vision.py` manda imágenes a Google (spike aprobado, datos tapados). No lo llama la app; queda fuera del release (FIX-11).
- No se corrió `/security-review` completo: se puede correr antes de 7-release.

## Carga y deuda
- Prueba de carga omitida: app local de un usuario; N2 medido en T8 (161 s y 350 s por foto) y en T16. Sin linter configurado → sin línea base de deuda.

## Smoke (para el usuario, ≈5 min)
1. Escanear una foto de comandas con rango en el nombre → aparecen avisos «Falta el recibo …» si corresponde.
2. Pestaña ④ Revisión: el recorte se ve, los candidatos se pueden clicar, «Confirmar así» recalcula el día.
3. Volver a escanear ese día → el recibo confirmado sigue «revisado» (ver FIX-1: hoy puede perderse).
4. Exportar el Excel del día → DATOS OCR tiene las columnas Recibo y Motivo, fila amarilla si dudoso.
Resultado (usuario, 2026-10-18): 1, 2 y 4 bien. 3 sin verificar: el recibo confirmado sale de ④ y la UI no muestra los «revisado» en ningún lado → FIX-12.
