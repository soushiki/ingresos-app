# 01 · Research — modo contador web (Pyodide, todo local)

## Summary
- **Spike PASS (2026-10-26):** el núcleo actual sin cambios (`leer_crudo` → `construir` → `libro_a_excel`) corre en **Pyodide 314.0.7** (Python 3.14.2) con openpyxl 3.1.5 + et_xmlfile 2.0.0 instalados desde wheels locales (`unpackArchive`, cero red). Crudo real de sept. 2026 (30 días, 1,5 MB) → Excel **idéntico** al de CPython: 5 hojas, 25.902 celdas, 0 diferencias (valor, formato, negrita, relleno). `leer_xlsx` del extracto de sept.: 643 líneas, mismo hash.
- Tiempos (Node, PC del usuario): cargar Pyodide ≈ 1,0 s, cálculo del mes ≈ 2,1 s (CPython 1,0 s). Núcleo Pyodide = 14 MB + ~0,4 MB de wheels; el núcleo contable es solo stdlib + openpyxl (nada de pandas/xlrd/PDF/numpy). El extracto ya es solo .xlsx.
- **Hosting:** Netlify, carpeta estática, **Pyodide y wheels auto-alojados** (sin CDN: no hay SRI oficial y así `connect-src 'self'` bloquea cualquier salida). URL fija por versión: un deploy por tag (permalink del deploy) o subcarpeta `/vX.Y.Z/`; elegir en diseño.
- CSP candidata (sin probar en navegador): `default-src 'none'; script-src 'self' 'wasm-unsafe-eval'; worker-src 'self' blob:; connect-src 'self'; img-src 'self' blob: data:; style-src 'self'`. Pyodide en un Web Worker de tipo módulo; descarga por Blob + `URL.createObjectURL`.
- Lo que falta portar no es el núcleo sino el **pegamento de `app.py`**: config (`_cont_cfg`: negocio, NIT, puentes), repartir el extracto por día (`cont_extracto`, app.py:609–621) y las alertas `cambios` de `cont_excel`.

## Options compared
| Pregunta | Opción | Fit | Costo | Madurez | Veredicto |
|---|---|---|---|---|---|
| Correr el núcleo | Pyodide 314.0.7 + núcleo Python tal cual | probado, mismo resultado | 14 MB 1ª carga | estable | **elegida** (un solo cálculo, ADR-002) |
| | Reescribir en JS (SheetJS) | dos cálculos que divergen | alto | buena | descartada |
| Instalar openpyxl | wheels locales + `unpackArchive` | sin red | nulo | probado | **elegida** |
| | micropip desde PyPI | llamada de red en runtime | nulo | buena | descartada (rompe «nada sale») |
| Servir Pyodide | auto-alojado en el sitio | `connect-src 'self'` | ~14 MB por versión | estable | **elegida** |
| | jsDelivr fijado | sin SRI oficial | 0 | buena | descartada |
| URL por versión | permalink de deploy (CLI, ID por tag) | bueno | gratis | blog 2021, retención no confirmada | candidata |
| | subcarpeta `/vX.Y.Z/` en un solo sitio | bueno, URL legible | +14 MB por versión | estándar | candidata |

## Codebase map
- App: `app.py` (Flask 127.0.0.1:5050, `iniciar.bat`); tests = `python probar_<x>.py` (27; ADR-004 → `probar_datos_ocr.py`); release = VERSION + CHANGELOG + tag (v1.9.1).
- Libro: `cont_excel` (app.py:872) → `parser_module/contable/asientos.py:309 construir` → `exportar.py:129 libro_a_excel` (+ `puc.py`, `documentos.py`, `parser_module/numeros.py`).
- Crudo: `exportar.py:216 crudo` / `:271 leer_crudo` (sha256, versión 1). Extracto: `extracto.py:220 leer_xlsx` + `extracto_reglas.json`.
- JSON del paquete se leen con `Path(__file__)` al importar → hay que copiar `parser_module/**/*.py,json` al FS de Pyodide (el spike lo hace).
- Solo captura (no va al navegador): `ocr_module/*`, `relectura.py` (threads), `llm_fallback.py` (requests), `soporte*.py` (sqlite3, documento soporte).
- Spike: `spikes/pyodide/` (`nucleo.py`, `ref.py`, `run.mjs`; Node + `npm i pyodide@314.0.7`).

## Risks / unknowns
- CSP y Worker **no probados en navegador real** (el spike corrió en Node); Safari y `'wasm-unsafe-eval'` dudoso.
- 1ª carga ~14–15 MB: en el internet del contador puede tardar; caché del navegador lo mitiga. Medir en navegador.
- Netlify: retención de permalinks en plan gratis y límite por archivo (wasm ~10 MB) sin confirmar; snippet injection/analytics deben quedar apagados.
- `parser_module/contable/terceros_cuentas.json` está en .gitignore (datos reales): ¿va en la página o el contador lo carga? Lo mismo para `por_confirmar.json` y la config (negocio/NIT) → requisitos.
- Archivos subidos = no confiables: `leer_crudo` ya valida (sha256, topes, RecursionError); el extracto tiene tope 5 MB. Memoria wasm 4 GB, móvil mucho menos.
- Contrato crudo v1 (memoria contador-stable): la página de cada versión debe seguir leyendo crudos v1 → test con el crudo de v1.9.1.

## Sources
- https://pyodide.org/en/stable/usage/packages-in-pyodide.html
- https://pyodide.org/en/stable/usage/downloading-and-deploying.html
- https://pyodide.org/en/stable/usage/webworker.html
- https://pyodide.org/en/stable/usage/type-conversions.html
- https://micropip.pyodide.org/en/stable/project/api.html
- https://www.netlify.com/blog/2021/12/07/unique-permalinks-for-every-version-of-your-site/
- https://docs.netlify.com/routing/headers/
- https://docs.netlify.com/build/post-processing/snippet-injection/
- https://sqlite.org/wasm/doc/tip/csp.md
