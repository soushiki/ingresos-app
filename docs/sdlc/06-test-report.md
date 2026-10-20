# 06 · Informe de pruebas — ciclo Rappi (01c #6), iteración 1

## Summary
- **FALLA (vuelve a 5-implement).** Las 18 suites pasan, pero el papel de Rappi pierde ID y valor en el flujo real de subida (FIX-1).
- Cobertura: R1 (lectura, construir, sin total, ID fuera de numeración) · R2 (mismo ID = 1 venta + aviso) · R3 (respaldo v1.4.0,
  v1.3.0 intacto): con prueba. Falta: R1 por `leer_hoja` (la ruta de la foto) → se agrega con FIX-1.
- Septiembre (T4): 13452501 = [01f] vs manual ≈ [01f]; la diferencia son papeles de 17 días que no están en el libro, no lectura.

## Failures
- Ninguna en suites (`probar_*.py` todas en verde; `probar_imagen.py` es herramienta, no suite).

## Review findings (diff 9860ae9..HEAD, revisión propia)
1. **Alta — FIX-1.** `relectura.leer_hoja` → `un_trozo` (l. 175): recorte con un solo doc «venta» va a `leer_recibo`, que re-parsea con
   `parse_venta`. Prueba con motor falso que devuelve el papel real: `rappi=None, numero='', valor=0, medio=''`, «dudoso».
   O sea, en la app el papel de Rappi sigue entrando como venta sin número ni valor. T4 midió desde el texto guardado y no lo vio.
2. **Media — FIX-2.** `validar` pide hora y mesa a todo doc «venta»: cada papel de Rappi queda «dudoso» (Falta la hora / la mesa).
3. Baja (sin tarea): `validar.faltantes` y `cruces` siguen tomando todo `tipo == venta`; el ID largo nunca está en los números del
   nombre de la foto, así que no crea faltantes falsos. Queda anotado.
4. Abierto de T4: 11-sep, 28150502 baja [01f] al re-leer; causa sin investigar. Se revisa en el smoke tras FIX-1.
- `/security-review`: no aplica (exposed no; no toca auth, BD ni secretos; el input es texto OCR ya existente).

## Debt check
- Sin linter en el proyecto; el diff suma 1 función (`parse_rappi`, 16 líneas) y 1 helper (`_es_comanda`). Sin DEBT nuevo.

## Smoke (para después de FIX-1/FIX-2, ≈ 5 min en la app local)
1. Subir `2/comandas/85319-318-rappi.jpg` como «comandas» → aparece el papel con ID 1000000001, $25.000, medio Rappi, sin «dudoso».
2. En ④ del 02-09: fila 13452501 débito 25.000, tercero Rappi, medio App; débito = crédito.
3. Subir la misma foto otra vez → una sola fila 13452501 y aviso de duplicado.
4. Comandas 85318 y 85319 sin faltantes ni «fuera de secuencia».
5. Ver el 11-09: anotar de dónde sale el −[01f] en 28150502.
Resultado: pendiente (bloqueado por FIX-1).
