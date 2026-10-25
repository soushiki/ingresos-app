# 06 · Test report — M-25 Indra OCR · Iteración 3 (T9–T10)

## Summary
- **PASA** R5 y R7 (las dos Should de I3); N2/N5 cubiertos. Diff: `974410e..HEAD` (6 archivos, +93/−5; código: `ocr_module/indra.py`, `probar_indra.py`, `probar_motores.py`, README).
- Sumando I1–I3: Musts R1, R2, R3, R4, R6 pasan (I1/I2); falta solo R8 (licencia), que es de 7-release. Meta ≤ 2/103 (Should Q3) no se alcanza → M-26 en 08.
- Sin defectos que bloqueen → `next: 7-release`.

## Cobertura (Given/When/Then de I3)
| criterio | prueba | resultado |
|---|---|---|
| R5 cierre normal → trabajador termina ≤ 5 s | `probar_motores.py` (cerrar con trabajador vivo) + `atexit` | ✓ |
| R5 matar Flask → EOF cierra el trabajador ≤ 5 s | `probar_motores.py` (padre matado a la fuerza, `tasklist`) | ✓ |
| R5 cierre con pedido colgado | `probar_motores.py` (`acquire(1 s)` y matar, ≤ 3 s) | ✓ |
| R5 un solo trabajador con el recargador | arranque perezoso (primer pedido) + `app.py` sin `debug`; nota README | ✓ por diseño (sin prueba automática) |
| R7 saludo `ready` 1.1.2, `numeros`, `upright` girada | `probar_indra.py` (6 ✓ con `indra_venv`; omitido limpio sin él) | ✓ |
| N5 misma foto → misma lectura | `probar_indra.py` (`numeros` ×2, `upright` ×2) | ✓ |

## Suite
- 22 `probar_*.py` OK, 0 fallos (2026-10-24, con `indra_venv`): `probar_indra.py` «OK: 0 fallos» (1 s), `probar_motores.py` OK (8 s, incluye los 3 casos de T10). `probar_imagen.py` y `probar_motores_falso.py` no son suites.

## Revisión (diff de I3)
- Sin defectos que bloqueen. Security-review no obligatorio (exposed: no; I3 no toca entrada, BD ni secretos).
- Menor 1 (aceptado): si `cerrar()` no consigue el candado en 1 s llama `_matar()` sin él, a la vez que el hilo colgado; `_matar` intercambia `self._p` por `None` antes de matar, así que el peor caso es un `close()` doble del log, que es inofensivo.
- Menor 2 (aceptado): en la hoja **sintética** de `probar_indra.py`, `rotate(90)` (antihorario, que endereza con giro 270) da `giro 0`; por eso la prueba solo usa el giro horario. Con fotos reales a 270° (6-test I2) salen 18/20 derechas, igual que a 90°. Si algún día falla una foto real a 270°, mirar `k == 4` en `indra_worker.py`.
- Menor 3 (aceptado): el README repite la nota del trabajador (viñeta de problemas + sección «Indra»). Queda así; se puede recortar en 7-release.

## Deuda / carga
- Sin linter en el proyecto → sin comparación; sin tarea DEBT. Carga: no aplica (app local de un usuario; N1 ya medido en I2).

## Humo manual (usuario, ≈ 5 min)
1. `python app.py`, subir una foto en ① (arranca Indra) → en `tasklist | findstr python` aparece un `python` de `indra_venv`.
2. Cerrar la app con Ctrl+C → a los ≤ 5 s ya no aparece en `tasklist`.
3. Repetir 1 y cerrar la ventana de la consola (sin Ctrl+C) → tampoco queda.
4. `indra_venv\Scripts\python.exe` no hace falta tocarlo: `python probar_indra.py` → «OK: 0 fallos».
- Resultado: pendiente del usuario.
