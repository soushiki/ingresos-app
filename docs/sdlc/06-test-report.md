# 06 · Test report — M-13 iteración 1 (T1–T6, 4db7e0f..f5566b2)

## Summary
- **FAIL (2 defectos)**: 18/18 `probar_*.py` en verde (`probar_imagen.py` es una herramienta de línea de comandos, no una prueba).
- Cobertura: R1 servidor cubierto (probar_faltantes 15, probar_revision +34, probar_relectura +3, probar_contable +6);
  R1/R2 en la interfaz solo se probaron a mano en el navegador (T5, T6). R2 falla en el caso más común (FIX-1).
- No se ejecutaron: ataques (exposed: no), prueba de carga (I1 no fija ninguna NFR de latencia), lint (no hay ruff ni flake8).

## Failures
- Ninguna en la suite.

## Review findings (revisión del diff a mano; sin hallazgos de seguridad)
1. **FIX-1 · R2 no avisa del día que se está pasando** (`static/contable.html:290`). `avisoFaltan()` solo cuenta los faltantes
   que ya están en el libro (`/api/contable/revision?estado=falta`). En «Pasar al libro», los marcadores nuevos están en `docs`
   (del escaneo) y aún no están guardados → escaneas una foto con un recibo omitido, pulsas «Pasar al libro» y no sale ningún aviso.
   El T6 no lo detectó porque la prueba simuló el `fetch`. Arreglo: sumar `docs.filter(d=>d.tipo==="faltante"&&d.estado==="falta")`.
2. **FIX-2 · Recibo contado dos veces al releer** (`app.py` `_conservar_revisados`). Una venta anotada a mano guarda
   `origen:"manual", de_foto:F`; si al releer F el OCR sí lee ese número, la clave `(venta, num, origen)` no empareja
   (`manual` ≠ `F`) → quedan las dos (reproducido: 2 ventas con el 85388). `marcar_duplicados` solo lo atrapa si los montos
   coinciden (`misma_venta`). Pasará más a menudo después de R5 (T11), que lee más números. Arreglo: para la clave, usar `de_foto`
   como origen cuando `origen=="manual"`; prueba en probar_revision.
3. Menor (no es FIX): si al anotar se cambia el número, `reconciliar` no empareja y el marcador del número original vuelve a salir al
   releer. Es visible (no hay pérdida en silencio); se acepta.
4. Menor: el aviso del Excel cuenta los faltantes de todo el libro, no solo los de `f1..f2`. Es aceptable para un aviso que no bloquea.
- Seguridad: el id se valida con una expresión regular hexadecimal, la fecha con ISO, el cuerpo tiene un tope de 64 KB, la lista
  blanca es compartida (sin id ni fecha), hay LOCK+_bloqueos, motivo ≤ 200, y la interfaz usa textContent/DOM. Bien.

## Debt
- No hay linter configurado. La iteración suma +98 líneas en app.py (3 helpers pequeños; la deduplicación de `_campos_revision` le quitó
  complejidad a confirmar). Sin tarea DEBT.

## Smoke result
- Pendiente: lo hace el usuario con la lista de STATE/chat tras FIX-1 y FIX-2.
