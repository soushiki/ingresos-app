# 06 · Test report — modo contador web, Iteración 1 (T1–T7)

## Summary
- **PASS.** Musts de la It. 1 cubiertos: R1 (crudo → Excel idéntico), R3 (nada sale), R4 (negocio/NIT), R6 (versión visible); R5 parcial (crudo v1 fijo + `contrato.mjs`; el bloqueo del deploy es T11). R2 (extracto) es It. 2: el núcleo ya lo prueba (`probar_libro.py`), la página aún no.
- Suite: 29/29 `probar_*.py` verdes + `node web/pruebas/contrato.mjs` verde (`probar_imagen.py` es herramienta manual).
- Revisión de código y de seguridad del diff `7183832..7ecd44b` (30 archivos, +2259/−76): sin defectos que bloqueen. 1 prueba de ataque nueva (fórmulas en el crudo) agregada a `probar_libro.py`.
- Smoke del usuario: el Excel de sept. real de la URL borrador = el de ② (T7, 2026-10-26).

## Coverage (R-id → prueba)
| R | Criterio | Prueba |
|---|----------|--------|
| R1 | 0 celdas distintas (valor + formato) | `probar_libro.py` (CPython vs camino HTTP de la app) · `contrato.mjs` (Pyodide vs CPython, 1124 celdas) · usuario con sept. real |
| R1 | versión ≠ 1, sha256, JSON roto, anidado → mensaje en español | `probar_libro.py` 31 casos + `contrato.mjs` 15 casos S2 (sin rutas ni trazas) |
| R3 | solo GET al mismo origen, CSP | `probar_web.py` (cabeceras, sin URLs remotas en código) · T6 pestaña Red · 6-test: cabeceras en vivo |
| R4 | negocio/NIT en el Excel y recordados | `probar_libro.py` (validación, sin fórmula) · T6 recarga en el panel |
| R5 | crudo v1 fijo produce el Excel esperado | `web/pruebas/datos/crudo_v1.json` + `contrato.mjs` (bloqueo de deploy → T11) |
| R6 | página muestra su versión y la del núcleo | T6/T7 manual (`v-pagina`, `v-nucleo`) |

## Failures
- Ninguna.

## Review findings (code + security, `exposed: yes`)
- Worker: datos entran como bytes a un `puente` fijo (nunca texto de `runPython`); topes y hondura en JS antes de Python; `nucleo.zip` verificado por sha256; manifiesto validado (versión, nombres de wheel). OK.
- Página: todo texto externo con `textContent`; sin `innerHTML`, sin script en línea; Blob URL revocada al reemplazar. OK.
- **Ataque nuevo (CWE-1236):** crudo con `=HYPERLINK("http://…")` en los 110 textos libres → 48 celdas como texto, 0 fórmulas activas (`exportar.texto`, FIX-12). Queda en `probar_libro.py`.
- Cabeceras en vivo (URL borrador): CSP = S4 exacta, nosniff, no-referrer, sin `Set-Cookie`, POST → 404, wasm `application/wasm`. OK.
- Nota (no defecto): si el Worker muere sin mensaje (p. ej. el navegador lo mata por memoria), la página queda en «Generando…»; con crudos de ≈ 1 MB es improbable → se anota para T12 (avance), no FIX.
- Nota (no defecto): `/v1.9.1/` va `immutable` 1 año; lo que cambie en la página (T8 extracto) debe salir en una carpeta de versión nueva, no en `/v1.9.1/` → tenerlo presente en T10.

## Attack tests / carga / deuda
- Ataques: `probar_libro.py` (32 casos de entrada) + `contrato.mjs` (15) + cabeceras en vivo. Sin API ni BD: enumeración, sesión, roles, SSRF, BD directa = N/A (S6).
- Carga: N/A — sitio estático en la CDN de Netlify, sin backend; la latencia del contador (NFR) se mide en T14. Referencia T7: 3,6 s en frío (carga + cálculo).
- Deuda: baja (`app.py` −63 líneas al mover el pegamento a `libro.py`); sin tareas DEBT.

## Smoke (usuario, ≈ 5 min, ya hecho en T7)
1. Abrir la URL borrador `/v1.9.1/`, escribir negocio y NIT. 2. Subir el crudo de sept. y «Generar Excel». 3. Comparar con el Excel de ② → **iguales**. 4. Recargar: negocio/NIT siguen ahí.
