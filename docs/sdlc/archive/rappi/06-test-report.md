# 06 · Informe de pruebas — ciclo Rappi (01c #6), iteración 1 · 2.ª pasada

## Summary
- **PASA → 7-release.** 18/18 suites en verde; FIX-1 y FIX-2 cerrados; smoke con la foto real del 02-09 en verde.
- Cobertura: R1 (lectura, construir, sin total, ID fuera de numeración, ruta `leer_hoja`, `validar` sin hora/mesa) · R2 (mismo ID = 1 venta,
  `contar=False` + «duplicado de») · R3 (respaldo v1.4.0, v1.3.0 intacto): todas con prueba.
- Septiembre (T4, 1.ª pasada): 13452501 = [01f] vs manual ≈ [01f]; la diferencia son papeles de 17 días que no están en el libro, no lectura.

## Failures
- Ninguna (`probar_*.py`, 18 suites; `probar_imagen.py` es herramienta, no suite).

## Review findings (diff 506cd89..HEAD, FIX-1 + FIX-2)
- `relectura.un_trozo`: el papel Rappi ya no va a `leer_recibo`; cae a la rama general (recorte guardado + `validar`). Correcto.
- `validar`: con `rappi=True` devuelve antes de hora/mesa/aritmética y antes del cruce con los números del nombre de la foto
  (el ID largo nunca está ahí): correcto. Sin hallazgos nuevos.
- Baja, sin tarea (de la 1.ª pasada): `validar.faltantes`/`cruces` toman todo `tipo == venta`; no crea faltantes falsos.
- `/security-review`: no aplica (exposed no; sin auth, BD ni secretos).

## Debt check
- FIX-1/FIX-2 suman 3 líneas de código; `_motivos_rappi` se borró (una sola regla en `validar`). Sin DEBT nuevo.

## Smoke (OCR local real, `escanear` por cliente de prueba, sin guardar en el libro)
1. `SEPTIEMBRE/2/comandas/85319-318-rappi.jpg` como «comandas» → 3 docs: 85319, 85318 y el papel Rappi
   (ID 1000000001, $25.000, medio Rappi, «validado», sin motivos, fecha 2026-09-02 por la carpeta). ✓
2. `construir("2026-09-02")` → fila 13452501 débito 25.000, tercero Rappi, medio App, «Ordenes: 1000000001»; débito = crédito. ✓
3. El mismo papel dos veces → una sola fila 13452501 de 25.000. ✓
4. Comandas 85318–85319: `faltan` = [], sin avisos de secuencia. ✓
5. 11-09, 28150502: recalcular desde los docs guardados da [01f] = lo guardado. El −[01f] de T4 venía de re-parsear el texto crudo
   (pierde las correcciones a mano), no de la ruta real de recálculo. Cerrado.

## Nota para 7-release
- Los docs ya guardados de sept. no tienen `rappi`: recalcular no basta. El runbook debe decir cómo re-leer los papeles de Rappi de sept.
  (volver a subir las fotos «…rappi…» de cada día, p. ej. 2, 3, 5, 6, 7, 11) y luego recalcular, con el respaldo v1.4.0 ya hecho.
