# 04 · Plan — M-26 Recuperar número con Indra (S)

## Summary
- 1 iteración, 3 tareas (S + M + S ≈ 2,5–3 h de trabajo + la corrida de medición de 103, larga y reanudable).
- Demo: el informe de `medir_precision.py --completo` muestra omitidos por «número» ≤ 2/103 y «recuperados con error» = 0.
- Sin deps, motores ni pantallas nuevas; ④ reusa el motivo nuevo. ADR-011 (R5 cercanía) sigue igual: solo se amplía «lo leído».

## Iteration 1 — el número que Indra vio cubre los «Falta N»
- [x] T1 (S) Guardar lo que leyó el segundo lector en el documento — R1 — `leer_recibo` deja en `doc["lectura"]["digitos"]`
  la unión ordenada (lista de int) de los sets de `leer_digitos` de todas sus pasadas; sin `leer_digitos` o todo `None` → la clave no está.
  Las ventas de un recorte con varios papeles (rama «docs» de `un_trozo`) no la tienen (fuera de alcance).
  — done when: test en `probar_relectura.py`: lector falso con {85334} en V0 y {85335} en V1 → `[85334, 85335]`; sin lector → sin clave;
  `probar_relectura.py` y `probar_motores_falso.py` verdes — files: `parser_module/contable/relectura.py`, `probar_relectura.py` — model: Sonnet — hecho: leer_recibo guarda lectura.digitos (unión ordenada de los sets de todas las pasadas; sin clave si no hay lector o todo None); 3 checks nuevos en probar_relectura.py
- [x] T2 (M) Paso 4 de `leer_hoja` con los números de Indra — R1, R2a — tras `_cercano(d, falta)` (qwen) sin resultado, probar con
  `doc["lectura"]["digitos"]` con la misma regla (único faltante igual; si no, único a ≤ 1 cifra y mismo largo; 0 o ≥ 2 → nada).
  Nueva constante `RECUPERADO = "Número recuperado por el segundo lector (Indra leyó {}): revísalo con la foto"` (`{}` = los números
  de Indra que cuadraron); `_por_cercania` recibe el motivo; queda «dudoso». Un número ya usado no se asigna (sale de `falta`, que se
  recalcula tras cada asignación, como hoy). qwen gana: si qwen ya da candidato, Indra no se mira.
  — done when: tests en `probar_contable.py` (los 5 de R2a): Indra ve el faltante → asignado + RECUPERADO; dos faltantes posibles →
  sin asignar; número ya tomado por otra venta de la foto → sin asignar; sin faltantes o `completa=False` → sin cambios; sin
  `lectura.digitos` → igual que hoy; `probar_contable.py`, `probar_relectura.py`, `probar_faltantes.py` verdes
  — files: `parser_module/contable/relectura.py`, `probar_contable.py` — model: Sonnet — hecho: paso 4 prueba lectura.digitos (sin los números ya usados en la foto) tras qwen con _cercano(d, falta, leidos); RECUPERADO y _por_cercania(d, n, motivo); 6 checks R2a en probar_contable.py
- [ ] T3 (S) Medir en la referencia de 103 — R2b — el informe de `referencia.medir` suma `recuperados` (ventas con el motivo
  RECUPERADO) y `recuperados_con_error` (de esas, las que tienen algún campo distinto a la referencia del número asignado: un número
  malo se ve como total/ítems de otro recibo); `medir_precision.py` los imprime en la línea «completo». Correr la medición completa de
  sept. (reanudable, una línea por foto; si pasa de ~30 min la corre el usuario desde su cmd con el comando que se le dé).
  — done when: test en `probar_precision.py` de los dos contadores; corrida real con omitidos por «número» ≤ 2/103,
  `recuperados_con_error` = 0, dudosos/validados con error no empeoran frente a `20261020-225729`; suite completa verde. Si queda > 2
  con 0 malos, se anota la diferencia en 06 y se publica igual (R2 riesgo)
  — files: `parser_module/contable/referencia.py`, `medir_precision.py`, `probar_precision.py` — model: Sonnet
