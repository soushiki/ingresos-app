# ADR-013 · Concepto y cuentas del extracto en `extracto_reglas.json`, ningún código PUC en el código

Estado: aceptado (2026-10-20, aprobado por el usuario)

## Contexto
El concepto sale de la descripción (prefijo anclado + signo). Las cuentas son reguladas y están «por confirmar»
con contabilidad (P2). El contador debe poder cambiarlas sin tocar Python.

## Opciones
1. Un `if/elif` en el código: rápido, pero cada cambio de cuenta o de banco sería un cambio de código.
2. Un clasificador ML: no hay historial (Won't).
3. **Una tabla ordenada en JSON** `{prefijo, signo, concepto, destino}` + `cuentas{clave:{codigo, fuente, por_confirmar}}`, como `normalizacion.json`.

## Decisión
Opción 3. Gana la primera regla que encaja. Si ninguna encaja, la línea queda «SIN CONCEPTO» → revisar (nunca se descarta).
El JSON se valida al cargar (prefijos no vacíos, signo ∈ {+,−,±}, destino conocido, código en el plan de cuentas o en PUENTES).

## Consecuencias
+ Se puede probar contra la hoja MOVIMIENTOS. + El contador edita un solo archivo. − Un JSON mal editado bloquea la importación (con un mensaje claro).

## Fitness test (`probar_extracto.py`)
- `extracto.py` no contiene literales de 8 dígitos. Mensaje: «ADR-013: código PUC fijo en extracto.py».
- Clasificar «Hoja 1» coincide en ≥98 % con MOVIMIENTOS, salvo las excepciones listadas. Mensaje: «ADR-013: reglas por debajo del 98 %».
