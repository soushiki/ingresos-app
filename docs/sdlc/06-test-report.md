# 06 · Test report — M-13 iteración 3 (T10 + T11, 03d83d8..bfd3704)

## Summary
- **PASS**: 18/18 `probar_*.py` en verde y corrida real `medir --completo --peores 20 --de-cero` (informe 20261019-135040).
- R5 (Should) cumple con ADR-011 (cercanía). Fitness en probar_relectura; avance reanudable en probar_precision (5 checks).
- Corrida real vs T10 (20261019-052322): omitidos 13 → **5/103** (4,9 %; todos de número), leídos 90 → 98,
  validados con error 7 → 7 (mismos números), dudosos 18 → 27 (los rescates quedan dudosos a propósito). Huella del libro igual.
- **N3** (≤ 2/103) **no se alcanza**; queda en ≈ 5/103 como aceptó el usuario en ADR-011. **N4 cumple** (aciertos suben, errores igual).
- Omitidos: 85334, 85375, 85389, 85390, 85411. 85334 es nuevo (en T10 se leía): variación del lector en la foto 3, no del código.
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
- Resultado: corrida hecha (2026-10-19, ≈ 3 h 40 min con una reanudación tras reiniciarse la terminal; el avance funcionó). Paso 3 (④) pendiente del usuario.
