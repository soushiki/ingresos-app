# 06 · Test report — M-25 Indra OCR · Iteración 1 (T1–T4)

## Summary
- **PASA** con lo que se puede probar sin `indra_venv`. Diff: `117d0d1~1..HEAD` (7 archivos de código, +625/−5).
- R4 (Must): cubierto — sin venv → Tesseract + aviso; cuelga/muere/miente → matar, reiniciar, 2 fallas → Tesseract por la sesión (`probar_motores.py`, trabajador falso); `capacidades` trae `motor`+`aviso` (nuevo check en `probar_contable.py`).
- R1 (Must): la regla «mismo `_enteros`, mismas reglas» está cubierta (`motores.leer_digitos`, `probar_motores.py`). La meta numérica (≥ 75 números / ≥ 96 totales sobre los 103) **no se pudo medir**: no hay venv de Indra → se mide tras T8 (instalador) con `medir_precision.py --completo`.
- N4 (dos hilos no mezclan) cubierto. N6: todas las `probar_*` siguen pasando en 3.15.

## Cobertura añadida
- `probar_contable.py`: `/api/contable/capacidades` → `motor ∈ {indra, tesseract}` y, sin venv, aviso «Indra no disponible…». El check que T4 decía haber agregado no estaba en el archivo.

## Suite (23 archivos)
- 21 OK, 0 fallos. `probar_imagen.py` es herramienta de línea de comandos (pide imagen) y `probar_motores_falso.py` es el trabajador falso: no son suites.

## Revisión (indra.py, motores.py, indra_worker.py, app.py, medir_precision.py)
- Sin defectos que bloqueen. Popen en lista, `-I`, sin shell, `HF_HUB_OFFLINE=1`, respuestas validadas (tipos, giro ∈ 0/90/180/270, |incl| ≤ 45, tamaño). Security-review no obligatorio (exposed: no; la entrada son fotos locales por tubería).
- Menor 1 (→ T10): `Cliente.cerrar()` toma el candado sin plazo; si un pedido está colgado al salir, el cierre espera hasta `INDRA_TIMEOUT_S` (10 s) antes de que el perro lo mate → R5 pide ≤ 5 s. Usar `acquire(timeout=…)` y matar si no lo consigue.
- Menor 2 (aceptado): el primer pedido de la sesión puede tardar hasta `INDRA_ARRANQUE_S` (30 s) dentro de una petición Flask. Coincide con ADR-016 (arranque perezoso); medir en T8.
- Menor 3 (aceptado): una línea > 1 MB se parte en dos; la primera no es JSON → falla → se mata el trabajador, así que no se desincroniza.

## Deuda
- El proyecto no tiene linter configurado; sin comparación posible. Funciones nuevas cortas (`pedir` es la más larga, ≈ 25 líneas). Sin tarea DEBT.

## Carga
- No aplica todavía: N1 (≤ 0,2 s por recorte) solo se mide con Indra real → T8/T9.

## Humo manual (usuario, ≈ 5 min)
1. Arrancar la app como siempre y abrir `http://127.0.0.1:5000/api/contable/capacidades` → debe decir `"motor": "tesseract"` y el aviso «Indra no disponible: se usa Tesseract».
2. Subir una foto de recibos de sept. ya conocida → mismos números y totales que en v1.6.0.
3. Revisar que no aparezca `logs/indra.log` con errores (sin venv no debería arrancar nada).
- Resultado: pendiente del usuario (el aviso visible en la interfaz es T7).
