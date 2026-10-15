# Módulo 2 · Texto plano → campos del cierre de caja

Recibe el texto del módulo 1 y lo convierte en los 12 campos: total vendido, número de órdenes, facturas anuladas,
propinas, base, cortesía, transferencias, efectivo, rappi, caja menor, domicilio y descontar.

## Probar
```bash
python probar_parser.py                       # 9 planillas de ejemplo con estilos distintos (deben salir todas ✓)
python probar_parser.py salida/planilla1.txt  # un texto real del módulo 1
python -m parser_module.cli salida/           # toda la carpeta del módulo 1 → cierres/cierres.csv y .json
```

## Qué generaliza (por qué sirve aunque cada día se escriba distinto)
- **Sinónimos y abreviaturas**: «Efec», «Domi», «Anul», «C. menor», «T. vendido», «# ord», «Nequi»…
- **Errores de lectura**: «Propinaz», «Efectlvo», «85O.OOO», «6l».
- **Cifras**: `1.250.000`, `$1'250.000`, `120k`, `120 mil`, `100 000`, `cuarenta y cinco mil`, `500.000 + 350.000`.
- **Disposición libre**: `etiqueta: valor`, `valor etiqueta`, tablas con `|`, valor en la línea siguiente,
  columnas (todas las etiquetas y luego todos los valores) y encabezado + fila de valores.
- **Extras**: tachones (`~~…~~`), «-» como cero, fechas en varios formatos, renglones sin campo → Notas.

## Nunca inventa
Cada campo sale `ok`, `revisar` (con la razón) o `faltante`. Un monto menor a 1.000 cuando los demás son de miles,
un valor con `[?]`, una suma de Nequi + Daviplata o dos valores distintos para el mismo campo quedan en «revisar».

## Cómo se adapta a TU negocio
1. Procesa tus planillas; al final lista las **etiquetas no reconocidas**.
2. Enséñalas una vez: `python -m parser_module.cli salida/ --aprender "gas=cajam" --aprender "aseo=cajam"`
   (se guardan en `alias_negocio.json` y valen para siempre).
3. Opcional en ese JSON: `"suma_medios": ["efectivo","transf","rappi"]` avisa si los medios de pago no suman el total.
   Si «Nequi» o «Daviplata» son solo una parte de las transferencias, ya se suman solos cuando no aparece el total.

## Apoyo con IA (opcional)
`--llm` pide al modelo local que complete SOLO campos faltantes. Solo acepta cifras que ya estén en el texto y
siempre los deja en «revisar».

Campos: total · ordenes · anuladas · propinas · base · cortesia · transf · efectivo · rappi · cajam · domicilio · descontar
