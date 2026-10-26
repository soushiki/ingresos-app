# T9 · Ataques en navegador (S2, S4)

Lado Python: `python probar_web.py` (sección T9, usa `ataques.py`). Lado navegador: esta lista, en la página armada
(`python herramientas/web_build.py`, servir `web/dist/` con las cabeceras de `_headers`, abrir `/vX.Y.Z/`).
Para elegirlos a mano: `python web/pruebas/ataques/ataques.py <carpeta>`. El nombre con `<script>` no puede existir
en disco en Windows: se arma con `new File([...], nombre)` + `DataTransfer` en la consola y se asigna a `#crudo.files`.

Pasa si: mensaje en español en la caja de error, sin traza ni rutas; ningún `alert`; ningún `<img>`/`<script>` nuevo
en el DOM; el botón vuelve a quedar activo; después un crudo bueno sigue generando el Excel sin recargar.

## Corrida 2026-10-26 · v1.9.1 · panel del navegador (Chromium) · servir_dist en 127.0.0.1:5072, CSP de S4

| Caso (crudo) | Resultado en la página | Tiempo | OK |
|---|---|---|---|
| `no_es_crudo.json` (un package.json) | «El archivo no es de datos crudos de Ingresos (falta «formato: ingresos-crudo»)» | 1,5 s (incluye cargar Pyodide) | ✓ |
| `exe_renombrado.json` (cabecera MZ/PE) | «El archivo no es un .json válido (¿está cortado?)» | 62 ms | ✓ |
| `anidado.json` (10⁵ corchetes) | «El crudo está demasiado anidado» (lo corta el Worker antes de Python) | 62 ms | ✓ |
| `gigante_25mb.json` | «El crudo pesa más de 20 MB; revise…» (app.js, sin leer el archivo) | 0 ms | ✓ |
| nombre `<script>alert("x")</script><img src=x onerror=alert(1)>.json` | nombre mostrado como texto literal; «no es un .json válido» | 57 ms | ✓ |

| Caso (extracto) | Resultado | OK |
|---|---|---|
| nombre `<img src=x onerror=alert(2)>.xlsx`, 6 MB | «El extracto «<img …>.xlsx» pesa más de 5 MB…» como texto; extracto quitado, crudo sigue elegido | ✓ |
| nombre `<script>x</script>.xlsx` (bytes MZ) | nombre mostrado como texto literal | ✓ |

- Alertas: 0. `<img>` en el DOM: 0. `<script>` en línea: 0. Botón activo tras cada error.
- Después de todos: `crudo_v1.json` → «Listo: reporte_contable_20261026.xlsx» en 121 ms (mismo Worker, sin recargar).
- Red: solo GET al mismo origen. Consola: solo el `fetch("data:…")` que se probó a propósito, bloqueado por `connect-src 'self'`.
