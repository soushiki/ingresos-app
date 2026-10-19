# 06 · Test report — M-13 iteración 3 (T10 + T11, 03d83d8..bfd3704)

## Summary
- **PASS (automático), falta confirmar N3/N4 con datos reales**: 18/18 `probar_*.py` en verde (`probar_imagen.py` es manual).
- R5 (Should) cumple con ADR-011 (cercanía, reemplaza ADR-010). Su fitness está en probar_relectura: sin faltantes no cambia ningún
  número; con 2 faltantes a 1 cifra no asigna ninguno. El avance reanudable de `medir` está en probar_precision (5 checks).
- N3 (≤ 2/103) sigue abierta por decisión del usuario (ADR-011 acepta ≈ 5/103). N2: tiempo +0 (no hay OCR nuevo).
- **Pendiente**: el resultado de `medir --completo --peores 20` con el código de bfd3704. La medición se hizo sobre las piezas de
  T10/T11 (13→4 y 15→5) y no con una corrida completa. Sin ella no se puede cerrar N4 (aciertos y dudosos no empeoran).
- No se ejecutaron: ataques (exposed: no), prueba de carga (N2 = +0 s), lint (no hay linter).

## Failures
- Ninguna.

## Review findings (diff 03d83d8..bfd3704: código +87/−11 en relectura, referencia y medir; revisado a mano)
1. `_cercano` bien: primero lo exacto y después a 1 cifra. Si hay 0 o ≥ 2 candidatos devuelve None. Si el largo es distinto, no
   asigna. `_leidos` descarta lo que no es dígito. Si `falta` se vacía a mitad del bucle, `_cercano(d, [])` da None.
2. `_por_cercania` quita «Falta el número» y «El recibo N no está», añade CERCANO y deja el recibo «dudoso»: pasa siempre por ④. Bien.
3. Menor, aceptado: si dos ventas están cerca del mismo único faltante, se lo lleva la primera, según el orden de lectura. Igual queda
   «dudoso» con la nota, así que el usuario lo ve en ④.
4. Menor, aceptado: el avance (`avance_<mes>_<variante>…json`) no guarda la versión del código. Si una corrida cortada se reanuda
   después de cambiar el lector, mezcla fotos leídas con dos versiones. Al empezar imprime «reanudo …: N fotos». Después de un
   cambio de código hay que usar `--de-cero`. Ahora no queda ningún avance pendiente en `datos/referencia/informes/`.
5. Menor: el avance guarda los documentos con `json.dumps(default=str)`. Si `leer_texto` devolviera fechas u objetos, las fotos
   reanudadas compararían como texto. Hoy los campos son str/int/float y probar_precision comprueba «reanudado = entero».
- Seguridad: no hay entradas nuevas. Las regex (`REC\w*\s*#…{4,6}`) son lineales. El avance se escribe de forma atómica
  (`.tmp` → replace). Sin hallazgos.

## Debt
- 4 funciones pequeñas nuevas en relectura (≤ 8 líneas cada una). Sin aumento de complejidad. Sin tarea DEBT.

## Smoke / confirmación (lo hace el usuario; ≈ 4 h sin atender, se puede apagar el PC y relanzar el mismo comando)
1. `python medir_precision.py --mes 2026-09 --fotos "<carpeta de las fotos>" --completo --peores 20 --de-cero`
2. Se compara con T10 (20261019-052322: omitidos 13, dudosos 18, validados con error 7). Se espera: omitidos ≈ 4–5,
   validados con error ≤ 7 y dudosos ≈ 18 + los rescatados (cada rescate queda dudoso a propósito).
3. ① Escanea la foto «5/…/85387 al 392» → en ④ los recibos rescatados muestran «Número corregido por cercanía…».
- Resultado: pendiente del usuario.
