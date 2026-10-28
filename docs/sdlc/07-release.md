# 07 · Release — ingresos_app (ciclo modo contador web)

## Runbook
Dos entregas salen del mismo `main` y del mismo `VERSION`:
- **App de captura** (Flask, 127.0.0.1): runbook sin cambios → `archive/recuperar-numero/07-release.md` (instalar, actualizar un PC, rollback por versión).
- **Página del contador** (estática, Netlify, sitio `libro-contable-web`): `https://libro-contable-web.netlify.app/vX.Y.Z/`. Sin backend, sin login, sin datos en servidor (R3).

**Build**: `python herramientas/web_build.py` → `web/dist/` (Pyodide/wheels de `web/web.lock` verificados por sha256, `nucleo.zip` por lista blanca, `_headers` S4, cada `web/publicadas/v*/` tal cual).
**Entorno (solo nombres)**: `NETLIFY_AUTH_TOKEN` (o `npx netlify-cli@27.12.0 login` una vez). Nada más; el token nunca va al repo ni a argumentos.

**Publicar una versión** (desde tu PC)
1. Suite verde: `for f in probar_*.py; do case $f in probar_imagen.py) continue;; esac; printf "$f: "; python $f | tail -1; done` + `node web/pruebas/contrato.mjs`.
2. `VERSION` + entrada en `CHANGELOG.md`; commit.
3. `python herramientas/web_deploy.py` → pruebas → **borrador** (URL impresa). Smoke en el borrador (abajo).
4. `python herramientas/web_build.py --publicar` → congela `web/publicadas/vX.Y.Z/` + `publicadas.lock`; commit. Desde aquí esa URL no cambia nunca (ADR-027): un arreglo = versión nueva.
5. `git tag vX.Y.Z && git push origin main --tags`.
6. `python herramientas/web_deploy.py` otra vez → checklist S4 en app.netlify.com (2FA, snippet injection vacío, analytics/forms/functions/identity apagados) → escribir «si» → producción.

**Health check** (en la URL de producción `/vX.Y.Z/`): carga sin errores de consola; DevTools → Red: solo GET al mismo origen; `curl -sI <url>/vX.Y.Z/` trae la CSP de S4, `nosniff`, `no-referrer`; `*.wasm` con `application/wasm`; crudo de prueba `web/pruebas/datos/crudo_v1.json` → Excel con 5 hojas; la raíz lista todas las versiones publicadas y cada una sigue abriendo.

**Smoke** (≈ 10 min, = 06 §Smoke): crudo de sept. + extracto Bancolombia de sept. → «Generar Excel» → igual al Excel de ② tras «subir extracto» con memoria vacía; un .xlsx cualquiera como extracto → «El extracto no sirve…», el crudo sigue; «Quitar» lo limpia.

**Rollback**: las versiones publicadas no se tocan; si `/vX.Y.Z/` falla, avisar al contador que use la anterior (`/vA.B.C/`) y publicar un arreglo como versión nueva. Si producción entera queda mal: app.netlify.com → Deploys → deploy anterior → «Publish deploy» (atómico). App de captura: `git checkout v1.9.1` (1.10.0 no migra soporte.db ni libro.json).

**CI**: no hay. Sugerido (GitHub Actions): suite + `contrato.mjs` + gitleaks (historial) + `pip-audit` + `bandit` + `npm audit` no aplica (sin package.json). Hoy no están instalados; pre-flight con grep (ver Releases).
**Monitoreo**: N/A por diseño: sitio estático sin backend, analytics apagados (no inyectar scripts, R3). Las cifras de latencia del contador → T14 (It. 3).
**Logs**: Netlify solo registra GET de archivos estáticos; ningún dato del contador viaja (todo en su navegador).

## Releases
- 2026-10-27 · v1.10.0 (modo contador web, It. 1–2) · preparada: VERSION + CHANGELOG; pre-flight: secretos (grep historial + dist) limpio, `_headers` = S4 sin CORS; falta: borrador + smoke del usuario, `--publicar`, push + tag, `--prod`.
- 2026-10-27 · v1.10.0 borrador `https://6ae13d6378ef28eafc27730c--libro-contable-web.netlify.app/v1.10.0/` · pruebas de web_deploy verdes; cabeceras = S4, wasm `application/wasm`; crudo_v1 → xlsx 17,7 KB en 4,1 s (panel), 0 errores de consola, solo GET al mismo origen. Falta el smoke del usuario con sept. real + extracto.
- 2026-10-27 · smoke parcial (usuario, borrador): crudo sintético + extracto real de sept. → Excel de la página = CPython `libro.generar` (5783/5783 celdas; solo difiere el NIT escrito) · resumen 643 nuevas / 123 por revisar / 28 días creados. Falta repetir con el crudo real (`data/entradas/ingresos_crudo_2026-09-01_2026-09-30.json`).
- 2026-10-27 · **smoke PASS** (usuario, borrador): crudo real de sept. (30 días, 1017 docs) + extracto real → Excel de la página = CPython `libro.generar` (= camino de ② «subir extracto», `probar_libro.py`): 24892/24892 celdas, solo difiere el NIT escrito; DATOS OCR 666 ventas / 154 cierre / 141 gastos / 97 facturas / 75 extracto; resumen 643 nuevas / 123 por revisar / 0 días creados. Siguiente: `--publicar` → push + tag → `--prod`.
- 2026-10-27 · **v1.10.0 en producción** `https://libro-contable-web.netlify.app/v1.10.0/` · web_deploy: pruebas verdes → checklist S4 confirmado por el usuario → `--prod`. Health check: CSP/nosniff/no-referrer en vivo, wasm `application/wasm`, raíz lista v1.10.0, app.js en vivo = `web/publicadas/v1.10.0` (sha256). Tag `v1.10.0` (21ce487).
