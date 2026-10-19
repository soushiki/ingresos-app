# 06 · Test report — M-13 iteración 2, segunda pasada (FIX-3/4, e771623..03d83d8)

## Summary
- **PASS**: 18/18 `probar_*.py` en verde (`probar_imagen.py` es una herramienta manual que pide una imagen, no es una prueba).
- FIX-3 y FIX-4 cerrados. R3, R4 y R6 cumplen. La iteración 2 está completa y sigue I3 (T10, compuerta R5).
- Cobertura: R3 en probar_validar (+5 nombres de escáner/cámara/fecha → `(None, [], True)`; `85490-492-501502-504-505` y
  `85560 al 85500` → marcador); FIX-4 en probar_revision (releer 2 veces dos fotos raras → un solo «No entiendo» por foto).
- No se ejecutaron: ataques (exposed: no), prueba de carga (no hay NFR de latencia en I2), lint (no hay linter).

## Failures
- Ninguna.

## Review findings (diff e771623..03d83d8, +22/−11 en 6 archivos, revisado a mano)
1. FIX-3 bien: un nombre con `\d{7}` o `AAAA-MM-DD` sale pronto con `(None, [], True)`. `entendido=False` solo cuando el nombre
   empieza por 4–6 cifras. Antes se quita el prefijo `comandas20260916_`, así que `comandas20260916_85627-628` sigue leyéndose.
2. FIX-4 bien: la clave de un faltante sin número es `("faltante", "", origen)`. Los faltantes con número y las ventas no cambian.
3. Menor, aceptado: un nombre que mezcla recibos y una fecha (`85560 al 565 2026-09-16.jpg`) se queda sin R5 y sin marcador.
   Es la opción prudente (ADR-009: mejor sin R5 que avisos falsos) y no aparece en la referencia.
4. Sigue pendiente para T10: `COMANDAS` en mayúsculas no recibe esperados en `medir`. Leer `por_causa` teniéndolo en cuenta.
- Seguridad: no hay entradas nuevas. Las regex son lineales. Sin hallazgos.

## Debt
- Sin funciones nuevas y sin crecimiento de complejidad. Sin tarea DEBT.

## Smoke result (≈ 5 min, lo hace el usuario; `python app.py` → http://127.0.0.1:5000/contable)
1. ① Escanea «3/comanda/85334-338 al 3341-343.jpg» → 6 recibos y el aviso «Nombre de la foto corregido: 3341 → 85341».
2. ① Escanea un PDF `comandas20261002_….pdf` → **ningún** marcador «No entiendo el nombre» en ④.
3. ① Escanea «10/comandas/85490-492-501502-504-505.jpg» → un marcador «No entiendo el nombre…» en ④ Faltan.
4. Vuelve a leer esa misma foto → sigue habiendo **un** solo marcador.
5. Abre LEEME §7 «Cómo tomar la foto» → se entiende en 30 s.
- Resultado: pendiente del usuario (las pruebas automáticas cubren los pasos 1–4 a nivel de función y de API).
