# ADR-023 · Plan B del gate N1: ampliar cobertura antes de cambiar de motor

Estado: aceptado (2026-10-25, pedido por el usuario)

## Contexto
T5 (jun–ago → sept–oct, 317 ítems de gasto) da 57,4 % por ítem: el motor decide el 61 % y acierta el 94 % de eso. El fallo es de **cobertura**, no de precisión: 124 ítems van a la puente «sin palabras conocidas». De esos, 67 son «Cuantías menores» con descripción «Recibo(s) 164, 165…» (sin palabras), y el resto son frases sin léxico («pago de compras», «propina», «día laborado», «carbón», «Facebook Direct») o personas (trabajadores que N5 no deja meter en el modelo). sklearn (plan B de 01) no arregla descripciones sin palabras.

## Opciones
1. **sklearn**: mejor peso de palabras; mismas descripciones vacías → misma puente. Dependencia nueva (N2).
2. **Bajar umbrales a ciegas**: sube cobertura y baja precisión sin medida.
3. **Ampliar cobertura con las capas que ya hay** y re-medir con T5.

## Decisión
Opción 3, en cuatro palancas:
- **Proveedores del cuadro completo**: el modelo de producción se mina con todos los meses (jun–oct). Los terceros persona van a `terceros_cuentas.json` (local, no versionado), nunca a `modelo_manual.json` (N5). El `Motor` lee ese archivo en la capa proveedor.
- **Frases**: el minado agrega bigramas («pago compras», «dia laborado») con la regla ≥ 2 y ≥ 80 %. Lo de mano va a `FRASES` solo con la cuenta de mayoría del manual. Los choques (domiciliario 28150501 vs 28150502) quedan «por confirmar» en `por_confirmar.json`.
- **Umbral de vecino**: barrer 0,60–0,80 y el empate 0,03–0,08. Se elige el valor más bajo que deje la precisión de lo decidido ≥ 90 %.
- **«Recibo N»**: al medir, la fila del manual se cruza con el texto OCR del papel del libro (es lo que el motor verá en la app). Sin cruce cuenta como fallo.

## Medición (sin fuga de datos)
El gate sigue como se aprobó (N1: entrena jun–ago, prueba sept–oct). Minar sept–oct y probar con sept–oct sería trampa. Además se reporta un walk-forward (jun–ago → sept, jun–sep → oct), que es como trabaja la app mes a mes.

## Consecuencias
+ Sin dependencias nuevas. Cada palanca se ve por separado en el informe.
− Si el gate sigue < 85 %, el usuario decide en un ADR nuevo: sklearn, o aceptar un N1 menor con puente + revisión.
