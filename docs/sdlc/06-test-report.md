# 6 · Test report — cierre de caja (v1.3.0)

<!-- borrador: sección T4 escrita en 5-implement; 6-test completa el resto -->

### T4 — Medir septiembre (aceptación e) — copia de datos/libro.json, 30 días, reglas de v1.3.0
- Saldo 2815 del mes (crédito − débito, 28150501+28150502): antes [cifra] → después [cifra] (−[cifra]).
- Días sin cierre (23): 2815 igual antes y después, [cifra]. Días con cierre (7: 01, 06, 07, 17, 20, 29, 30): de [cifra] a [cifra].
- Diferencia explicada: el saldo recalculado = suma de días sin cierre + [cifra]. Esos [cifra] son residuo de días con cierre donde
  el pago del cierre no cubre todo lo causado: 20-sep +[cifra], 30-sep +[cifra], 01-sep −[cifra], 06 −[cifra], 29 −[cifra], 07 −200.
  Los días 17-sep queda en 0.
- Ajuste R1 (cierre > papeles) en 5 días, total [cifra] al puente 13809501: 01-sep [cifra] · 06 [cifra] · 07 [cifra] · 20 [cifra] · 29 [cifra].
- Avisos «papeles > cierre»: 0 días.
- Débito = crédito: los 30 días cuadran (0 días con diferencia).
- Ojo: los días con ajuste R1 suben el débito/crédito guardado (p. ej. 20-sep [cifra] → [cifra]), así que el Excel los listará
  en «cambió desde que se confirmó»; el respaldo libro.antes-v1.3.0.json permite volver.
- Script y salida completa: scratchpad medir_sept.py / medir_sept.txt (fuera del repo).
