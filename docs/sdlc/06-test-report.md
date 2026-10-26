# 06 · Test report — M-26 Recuperar número con Indra (S), iteración 1

## Summary
- **PASS.** R1 y R2a: los 6 checks de R2a están en `probar_contable.py`, más 3 en `probar_relectura.py` (T1) y 3 en `probar_precision.py` (T3). Todo verde.
- **R2b cumplido.** Corrida `20261026-000348` frente a `20261020-225729` (103 recibos):
  omitidos 5 → **0** (meta ≤ 2), recuperados **4/4 con el número correcto**, validados con error 7 → 7, dudosos 26 → 27.
- Suite completa: 27/27 `probar_*.py` verdes (`probar_imagen.py` es una herramienta manual que pide una imagen; no es un test).

## Failures
— ninguna.

## Medición (detalle)
- Recuperados: 85334, 85375, 85389, 85411. El contador `recuperados_con_error` marca 3 (85334, 85375, 85411), pero en los 3 el
  **consumo coincide** con el del recibo de la referencia: el número es el correcto. Lo que falla en ellos es otro campo de un recorte
  sin encabezado: falta la fecha (85334, 85375), falta el pago por transferencia y la propina (85375), o sobra un descuento (85411).
  Los 3 ya van «dudosos» a ④. 0 números malos → se cumple el riesgo de R2.
- 85390 (antes omitido) ahora sale con número y como «dudoso». Le falta un domicilio (recorte cortado).
- Validados con error: sale 85520 y entra 85433. Los dos son el año leído 2025 en vez de 2026 (M-12). En la app lo corrige M-10
  (la fecha de la carpeta manda), pero `medir` compara la fecha impresa. No viene de M-26: 85433 no es un recuperado.
- Por campo, «mal» sube en fecha 7 → 8 y domicilio 4 → 5 (son los recibos que antes estaban omitidos y ahora se cuentan) y baja en
  consumo, propina, efectivo y medio. Lo demás queda igual.

## Review findings (revisión del diff, sin `/security-review`: exposed no; no toca auth, BD ni secretos)
- Nota (no bloquea): `recuperados_con_error` cuenta *cualquier* campo distinto, así que mezcla «número malo» con «recorte cortado».
  Si hace falta una alarma automática de número malo, mirar solo el consumo. Queda como nota en 08, sin tarea FIX.
- Nota: en el motivo RECUPERADO, `cuadran` lista todo lo que Indra vio a ≤ 1 cifra del número, aunque haya cuadrado exacto.
  Es solo texto para ④; está bien así.
- El código sigue la regla de R1: qwen gana, candidato único, no usa números de otras ventas de la foto y deja la venta «dudosa». Sin defectos.

## Debt
El proyecto no tiene linter. El diff es corto (+133/−15); `_dist` salió de `_cercano` como función aparte. No hace falta una tarea DEBT.

## Smoke (usuario, ≈ 5 min, `iniciar.bat` desde cmd)
1. Volver a leer en la app una foto de sept. 3–4 que tenga 85334 o 85375.
2. En ④, la venta sale «dudosa» con el motivo «Número recuperado por el segundo lector (Indra leyó …)».
3. El número coincide con el papel de la foto. Corregir la fecha o el pago y validar.
4. En esa foto ya no aparece «Falta 85334».
