# 06 · Test report — extracto bancario, iteración 2 (FIX-1, T6–T10)

## Summary
- **FAIL parcial: 20/20 suites verdes, pero la review halló 2 defectos (FIX-2 Must, FIX-3 Should).** Los dos están en el enlace salida ↔ factura (ADR-015).
- Cobertura de la iteración: R4 ✓ (casilla vacía = extracto, digitada manda + aviso, ningún recaudo doble, «usar extracto» deja 0 diferencias; T6/T10), R5 ✓ (revisión con fecha/descripción/valor/selector, asignar saca la línea, «recordada» al reclasificar, puente 51959501 mientras no se elige; T7/T9/T10), R7 ✓ (aviso «signo inesperado», idempotente tras FIX-1).
- Fuera de esta iteración: R3 (T11), R9 (T12), aceptación con el mes real (T13).
- Diff revisado: `0e76bd1..HEAD` sin el spike Indra (app.py +137, asientos.py +31, extracto.py +77, extracto_reglas.json +1, contable.html +38).

## Failures
- Ninguna en las suites (`probar_imagen.py` es CLI, no suite).

## Review findings (los dos confirmados con un script)
- **FIX-2 (Must):** la memoria pisa una línea `sin_asiento`. Con 2 facturas candidatas `clasificar` pone `sin_asiento` + «¿cuál factura?».
  Si el tercero está en la memoria, la línea pasa a `cuenta:recordada` y conserva `sin_asiento`. Resultado: `construir` no le da fila
  y la revisión no la lista (destino ≠ revisar). La salida de Bancos desaparece en silencio.
  Repro: «TRANSF A ANA PRUEBA» −50.000, memoria → 51050601, F1/F2 de 50.000 el 10 y el 11 → `cuenta:recordada 51050601 sin_asiento=True`.
- **FIX-3 (Should):** una factura puede quedar enlazada a dos líneas si están en días distintos. `usadas` vive solo dentro de
  una llamada a `clasificar` (un día) y `_facturas_cerca` no excluye las facturas ya enlazadas desde otros días. Repro: F1 de 50.000 el 10;
  salidas de −50.000 el 9 y el 11 → las dos quedan `factura F1`, sin asiento. Las dos aparecen «a confirmar», así que el usuario lo puede ver,
  pero mientras tanto falta una salida en el libro. Lo mismo pasa con un `factura_id` asignado a mano.
- Menores, sin tarea: «recordar» no reclasifica los otros días del mismo tercero que ya estaban importados (R5 habla del mes siguiente);
  un `asignada.factura_id` cuya factura se borró sigue sin asiento.

## Security review (entrada JSON y rutas nuevas; exposed: no)
- `fecha` se valida con ISO, `medio` con lista blanca (CASILLA_DESC), `cuenta` ∈ CATALOGO y `factura_id` ∈ documentos cercanos. `clave` solo se compara.
- Memoria escrita con tmp + replace después del libro y bajo LOCK. La UI arma con `el()` (texto) y sin innerHTML con datos del banco. Sin hallazgos.

## Load
- Asignar < 300 ms (T9) y importar < 3 s (T4). Sin ramp-load: es una app local de un usuario.

## Debt check
- El proyecto no tiene linter. `clasificar` creció a ~50 líneas con 4 pasos (regla → asignada → factura → memoria): el orden de esos pasos causó FIX-2. Sin DEBT aparte: el arreglo lo ordena.

## Smoke (usuario, ≈5 min, 127.0.0.1:5050 → Contable → ⑤ Extracto, con septiembre ya subido)
1. «Por revisar»: elige una cuenta para una «TRANSF A …», marca «recordar» y pulsa «Asignar» → la tarjeta desaparece.
2. Exporta el Excel → esa fila ya no está en 51959501, sino en la cuenta elegida.
3. Si aparece «Parece el pago de la factura …», pulsa «Sí» o «No». Con «Sí», la línea sale de la lista.
4. «Diferencias por medio»: pulsa «Usar extracto» en una diferencia → la diferencia desaparece.
- El agente hizo 1, 2 y 4 en el navegador durante T10 (94 → 93 por revisar; 0 diferencias). Falta la prueba del usuario.
