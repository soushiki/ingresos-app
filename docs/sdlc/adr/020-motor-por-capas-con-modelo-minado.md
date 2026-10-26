# ADR-020 · Motor por capas puro + modelo minado en JSON versionado, sin dependencias

Estado: aceptado (2026-10-25, aprobado por el usuario)

## Contexto
R5 pide un motor que aprenda del manual y diga por qué eligió cada cuenta. N2 no permite dependencias nuevas, N5 no deja meter valores, fechas ni nombres de personas en el código, y N3 pide menos de 30 s por mes. El manual (~1.537 filas) vive en `../data/`, fuera del repo.

## Opciones
1. **Leer el Excel manual en cada arranque**: depende de una ruta fuera del repo y metería datos personales en memoria y en el rastro.
2. **sklearn TF-IDF + LR**: mejor con palabras nuevas, pero es una dependencia nueva, hay que auditarla e instalarla en cada PC (es el plan B de N1).
3. **Un script `herramientas/minar_manual.py` → `contable/modelo_manual.json`** (léxico minado ≥ 2 y ≥ 80 %, proveedores, corpus del vecino), versionado. `Motor` aplica las capas en orden fijo. El vecino usa un índice de trigramas (top-20) y luego `difflib.SequenceMatcher`.

## Decisión
Opción 3. Las capas van en este orden: origen → enseñado → frases/LEXICO a mano → léxico minado → proveedor minado → vecino (ratio ≥ 0,75) → puente. Hay empate cuando la 1.ª y la 2.ª cuenta están a < 0,05 de distancia, y entonces va a la puente. Cada salida lleva `capa` y `motivo` con su fuente («parecido a julio fila 631»). `minar_manual.py --hasta 2026-08` genera el modelo para medir N1. Sin `--hasta`, genera el de producción.

## Consecuencias
+ Es explicable y rápido (~1 ms por ítem), y funciona sin internet ni el Excel.
+ Volver a minar es un comando, y el diff del JSON muestra qué aprendió.
− Tolera menos palabras nuevas que TF-IDF. Si N1 < 85 %, se escribe un ADR nuevo con sklearn.
− Los errores del manual entran por la regla de mayoría hasta que conteste el contador (ADR-022 los corrige con alias).

## Fitness tests (`probar_clasificacion.py`)
- `clasificar.py` y `reclasificar.py` importan solo la stdlib y el paquete `parser_module`. Mensaje: «ADR-020: dependencia nueva en el motor».
- `modelo_manual.json` no trae números de ≥ 4 cifras, fechas ni tokens de la lista de terceros persona. Mensaje: «ADR-020/N5: dato personal o valor en el modelo».
- 1.000 ítems de sept. se clasifican en < 5 s. Mensaje: «ADR-020/N3: motor lento».
