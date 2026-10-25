# ADR-025 · N1 baja al nivel medido; lo que el motor no decide va a la puente y a revisión

Estado: aceptado (2026-10-25, pedido por el usuario; reabre N1 de 02, cierra ADR-024)

## Contexto
Tres mediciones con el mismo gate (entrena jun–ago, prueba sept–oct, 317 ítems de gasto):
- T5: 57,4 %.
- T5c, ADR-023: 67,2 %, con cobertura 77 % y precisión de lo decidido 87,3 %.
- T5d, spike sklearn de ADR-024: 68,8 % (+1,6), con precisión de lo decidido 84,2 %. La capa ml decide 15 ítems y acierta 5.

El techo no es el motor sino el dato: descripciones sin palabras («Recibo 164»), personas y un manual inconsistente (4 cuentas con ≥ 10 ítems < 60 %: 51355001, 13452501, 51952501, 14050502). Walk-forward jun–sep → oct da 77,5 %: el motor mejora con cada mes que se digita.

## Decisión
- **N1 nuevo** (mismo corte jun–ago → sept–oct, por ítem, con alias): acierto ≥ **67 %** (medido 67,2 %) **y** precisión de lo decidido ≥ **85 %** (medido 87,3 %). Es un piso de regresión: ninguna task posterior puede bajarlo.
- **Lo no decidido va a la cuenta puente con motivo y a revisión** (R3, Q2 de 02). El usuario o el contador lo corrige en la tarjeta (T9/T11), y `aprender` lo vuelve «enseñado».
- **Regla por cuenta** (≥ 10 ítems < 60 %): deja de ser gate. Esas cuentas salen en el informe R9 y en la lista del contador (T12), porque el problema es del manual.
- **sklearn fuera**: se desinstala (scikit-learn, scipy, joblib, threadpoolctl). T5e y T5f se descartan. N2 vuelve completo: sin dependencias nuevas. `herramientas/spike_ml.py`, `requirements-entrenar.txt` y `logs/spike_ml_2026-10-25.txt` quedan como registro.
- **Re-medir** con `medir_clasificacion.py` al cerrar cada mes, y en 6-test.

## Consecuencias
+ It. 2 arranca ya; sin dependencias nuevas ni modelo extra que copiar a cada PC.
− Uno de cada tres ítems (≈ 23 % sin decidir más los errores) necesita una mano. La revisión se vuelve parte del flujo, no la excepción.
− Si la precisión decidida cae bajo 85 % en un mes nuevo, se suben los umbrales (más puente) antes que aceptar errores en los libros (`regulated: yes`).
