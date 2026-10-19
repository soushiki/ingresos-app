# 06 · Test report — M-13 iteración 1, segunda pasada (T1–T6 + FIX-1/FIX-2, 4db7e0f..fd90152)

## Summary
- **PASS**: 18/18 `probar_*.py` en verde (`probar_imagen.py` es una herramienta de línea de comandos, no una prueba).
- Cobertura: R1 servidor cubierto (probar_faltantes 15, probar_revision +35 con FIX-2, probar_relectura +3, probar_contable +6);
  R1/R2 en la interfaz probados a mano en el navegador (T5, T6, FIX-1). Los dos Musts de I1 (R1, R2) cumplen.
- No se ejecutaron: ataques (exposed: no), prueba de carga (I1 no fija ninguna NFR de latencia), lint (no hay ruff ni flake8).

## Failures
- Ninguna.

## Review findings (diff f5566b2..fd90152, revisado a mano)
1. FIX-1 cerrado: `avisoFaltan(true)` suma los marcadores `falta` de `docs` a los del libro. «⬇ Excel» sigue contando solo el libro.
2. FIX-2 cerrado: la clave de `_conservar_revisados` usa `de_foto` cuando `origen=="manual"`. La venta anotada gana sobre la relectura
   y queda una sola. Una venta manual sin `de_foto` queda con la clave `(venta, num, "")` y no choca con nada. Bien.
3. Menor (no es FIX): si se vuelve a pasar un día **que ya está en el libro** con marcadores sin anotar, ese marcador se cuenta
   dos veces (libro + pantalla), así que el aviso dice N+1. Solo exagera un aviso que no bloquea; se acepta.
4. Siguen aceptados de la primera pasada: si se cambia el número al anotar, el marcador vuelve a salir al releer (es visible). El aviso
   del Excel cuenta todo el libro, no solo `f1..f2`.
- Seguridad: los arreglos no tocan validación, entrada ni bloqueo. Sin hallazgos.

## Debt
- Sin cambios: +1 línea en app.py y +2 en contable.html. Sin tarea DEBT.

## Smoke result (≈ 5 min, lo hace el usuario; `python app.py` → http://127.0.0.1:5000/contable)
1. ① Escanea una foto con un recibo omitido (p. ej. la de 85387–85390) → sale la fila «falta 85388» y ④ tiene insignia.
2. Pulsa «Pasar al libro» sin anotarlo → aparece «Quedan 1 recibo(s) sin anotar»; elige Cancelar.
3. ④ Revisión → Faltan → Anotar con un monto → la insignia baja y el día suma el monto.
4. Vuelve a leer la misma foto → la venta 85388 sale **una sola vez**.
5. Otro faltante → «No existe» con motivo → desaparece y «⬇ Excel» ya no avisa.
- Resultado: pendiente de que lo marque el usuario.
