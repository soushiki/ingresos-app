# 06 · Test report — modo contador web, Iteración 2 (T8–T11)

## Summary
- **PASS (automático); falta el smoke del usuario con el extracto real de sept.** Musts de la It. 2: R2 (extracto), R5 (crudo v1 bloquea el deploy), R6 (URL fija por versión), S2/S4 (ataques, cabeceras). R1/R3/R4 siguen verdes de la It. 1.
- Suite: 30/30 `probar_*.py` verdes (incl. `probar_motores_falso.py`; `probar_imagen.py` es herramienta manual) + `node web/pruebas/contrato.mjs` verde.
- Revisión de código y de seguridad del diff `183e005..b87c762` (14 archivos, +463/−44): sin defectos que bloqueen; 2 notas menores, sin FIX.

## Coverage (R-id → prueba)
| R | Criterio | Prueba |
|---|----------|--------|
| R2 | crudo + extracto = app tras «subir extracto» | `probar_libro.py` (CPython vs camino HTTP de la app) · `contrato.mjs` (Pyodide vs CPython, 1245 celdas, 0 distintas) |
| R2 | extracto > 5 MB / no Bancolombia → motivo, crudo sigue | `probar_libro.py` (gigante, .exe, sin columnas, no bytes) · `contrato.mjs` (> 5 MB en JS, «no es .xlsx») · página T8 en el panel |
| R2 | líneas en días que el crudo no trae crean el día | `probar_libro.py` + `contrato.mjs` (días 09-18 y 09-30 creados, resumen llega a la página) |
| R5 | crudo v1 fijo → Excel; si no, no hay deploy | `contrato.mjs` (versión actual + cada `/v*/` publicada de dist) · `probar_web.py` (ejecutar falso: cualquier prueba rota → 0 deploys) |
| R6 | URL por versión no cambia | `probar_web.py` (1 byte cambiado / sobra / falta / carpeta a mano → build se niega; `--prod` solo si está en `publicadas.lock`) |
| S2/S4 | ataques en navegador, cabeceras | `web/pruebas/ataques/` + CHECKLIST.md (T9) · `probar_web.py` |

## Failures
- Ninguna. (Primer intento corrió con `python -I`, que saca la raíz del repo de `sys.path`: error de la corrida, no del código.)

## Review findings (code + security, `exposed: yes`)
- Página: extracto y nombres con `textContent`; tope de 5 MB antes de leer; error del extracto quita solo el extracto. OK.
- Build: publicadas verificadas byte a byte + Pyodide/wheels que su manifiesto pide; versión publicada no se rearma desde `web/src`; `.gitattributes -text` evita que autocrlf rompa el sha256. OK.
- Deploy: token solo por `netlify login`/env, CLI fijada (`netlify-cli@27.12.0`), `--prod` con «si» escrito + checklist S4. OK.
- Nota (no defecto): `url_de` lanza traza si netlify no imprime JSON (el deploy ya salió; solo falla el mensaje) → anotar en 08.
- Nota (no defecto): `verificar_publicadas` da `KeyError` (no `BuildError`) si alguien edita el lock a mano y quita `manifiesto.json` → anotar en 08.
- Nota: `contrato.mjs` «motor sigue generando» tolera ±64 B (core.xml lleva la hora); la igualdad de celdas sigue siendo exacta en los otros chequeos.

## Attack tests / carga / deuda
- Ataques: `probar_libro.py` (32) + `contrato.mjs` (16 S2) + `ataques/` (no-crudo, .exe, anidado 10⁵, 25 MB, nombre `<script>`). API/BD/sesión/SSRF = N/A (estático, S6).
- Carga: N/A (sin backend); latencia del contador → T14.
- Deuda: `web_build.py` +116 líneas en funciones chicas (`leer/verificar_publicadas`, `publicar`, `_version_nueva`); sin subida de complejidad → sin DEBT.

## Smoke (usuario, ≈ 10 min) — pendiente
1. `python herramientas/web_deploy.py` → corre las pruebas y deja una URL borrador (no pregunta `--prod`: v1.9.1 no está publicada).
2. En la URL borrador `/v1.9.1/`: crudo de sept. + extracto Bancolombia de sept. → «Generar Excel»; anotar el resumen (nuevas / por revisar / días creados).
3. Comparar con el Excel de ② tras «subir extracto» del mismo extracto, con memoria vacía → iguales.
4. Elegir un .xlsx cualquiera como extracto → mensaje «El extracto no sirve…», el crudo sigue elegido; «Quitar» lo limpia.
