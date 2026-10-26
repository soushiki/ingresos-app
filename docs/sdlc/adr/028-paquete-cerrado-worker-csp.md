# ADR-028 · Paquete cerrado: núcleo por lista blanca, Pyodide en Worker, CSP sin salidas

Estado: aceptado (2026-10-26, aprobado por el usuario en 3-design del modo contador web); spike T1 PASS 2026-10-26: Chrome 156, Edge 156 y el navegador del panel cargan Pyodide 314.0.7 en Worker módulo + openpyxl con la CSP de S4 **sin nada extra**; eval y fetch externo quedan bloqueados dentro del Worker (`spikes/pyodide/csp/`). Para T6: poner favicon propio (único 404).

## Contexto
R3 «nada sale del PC» y S1–S5: el sitio es público, los archivos subidos no son confiables y el repo tiene datos que no pueden publicarse (`terceros_cuentas.json` con personas, `datos/`). Copiar `parser_module/**` entero (como el spike) arrastraría el motor de clasificación y lo que se agregue después.

## Decisión
- **Lista blanca** en `herramientas/web_build.py`: solo los módulos que `libro.generar` importa (`contable/{libro,asientos,documentos,exportar,extracto,puc}.py`, `numeros.py`) y sus JSON versionados (03 §4). Los dos `__init__.py` van **vacíos** en el zip: los reales importan `clasificar` (Motor, terceros) y el parser OCR. Todo lo demás queda fuera aunque exista. Nombres prohibidos (`terceros_cuentas.json`, `modelo_manual.json`, `libro*.json`, `contable.json`, `datos/`, `*.db`) hacen fallar el build.
- **Pyodide en un Worker módulo**; la UI nunca corre Python. Sin `micropip`, sin `loadPackage` de red: wheels por `unpackArchive` desde `/py/`.
- **Cabeceras** en `web/dist/_headers` para `/*`: la CSP de S4 + `nosniff`, `no-referrer`, `Permissions-Policy` vacía. Snippet injection y analítica de Netlify apagadas.
- Si el spike T1 muestra que Pyodide necesita algo más que `'wasm-unsafe-eval'`, se agrega solo a la ruta del Worker y se anota aquí; nunca `connect-src` fuera de `'self'`.

## Consecuencias
+ Lo que llega al navegador es una lista corta y revisable; agregar un módulo es un cambio visible en el build.
− Si `libro.py` empieza a importar un módulo nuevo, el build falla hasta sumarlo a la lista (a propósito).

## Fitness test (`probar_web.py`)
- `nucleo.zip` = exactamente la lista blanca; ningún nombre prohibido → «ADR-028: archivo fuera de la lista blanca en el paquete».
- `_headers` trae la CSP exacta de S4 → «ADR-028: falta la CSP o cambió».
- En `web/src/*` no hay `http://`/`https://`, `micropip`, `innerHTML`, `eval(` ni `new Function` → «ADR-028: salida o ejecución no permitida».
- `libro.generar` importado en un intérprete limpio con solo la lista blanca en `sys.path` funciona → «ADR-028: falta un módulo en la lista blanca».
