# ADR-022 · Las decisiones del contador en `por_confirmar.json`; la validación PUC dentro del motor

Estado: aceptado (2026-10-25, aprobado por el usuario)

## Contexto
`regulated: yes`. Las 8 decisiones del informe de inconsistencias (1405 vs 1435, domicilios, Rappi, 513530 → 513555/513535, 519575…) son del contador y van por regla de mayoría marcadas «por confirmar» (triage). R4 pide que ninguna cuenta salga fuera del PUC, y R10 pide que al contestar se cambie un JSON sin tocar código.

## Opciones
1. **Constantes en `clasificar.py`** (como `LEXICO` hoy): el contador no las ve y cambiarlas obliga a tocar código.
2. **Ponerlas en `contable.json`**: mezcla la configuración del usuario (reporta, puentes) con decisiones contables que tienen su propio estado.
3. **`contable/por_confirmar.json`**: `{alias: {codigo_manual: codigo_puc}, decisiones: [{id, pregunta, regla_usada, cuenta, estado, fuente, afecta}], umbrales: {…}}`. `puc_valida(cuenta)` aplica el alias y luego `puc.revisar`. Si el resultado no es «ok» ni «propia», va a la puente con el motivo.

## Decisión
Opción 3. `puc_valida` es el último paso de `Motor.clasificar_item`, también para lo enseñado y lo manual. En lo manual solo avisa, no cambia la cuenta. Las puentes siguen saliendo de `contable.json` (ya existen ahí). `por_confirmar_pdf.py` (R10) lee el mismo JSON.

## Consecuencias
+ Contestar al contador = cambiar `estado` y `cuenta` en un JSON y luego «Reclasificar mes».
+ Cada decisión nombra su autoridad (`fuente`: «Decreto 2650 art. 6–7», «contador, pendiente»).
− Hay un archivo más que mantener versionado.

## Fitness tests (`probar_clasificacion.py`)
- Cada cuenta que sale de `Motor` (sin `manual`) pasa `puc.revisar` ∈ {ok, propia} o es una puente. Mensaje: «ADR-022: cuenta fuera del PUC».
- Cada entrada de `decisiones` trae `estado` ∈ {por confirmar, confirmado} y `fuente`. Mensaje: «ADR-022: decisión sin estado o sin fuente».
- `clasificar.py` no trae códigos de 8 dígitos fuera de `LEXICO`/`FRASES`. Mensaje: «ADR-022: decisión contable escondida en el código».
