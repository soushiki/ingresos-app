# 02 · Requirements — modo contador web (Pyodide, todo local)

## Summary
- **Meta:** el contador abre una URL fija por versión (Netlify, estática), sube el crudo (ADR-004) y, si quiere, el extracto .xlsx; su navegador arma y descarga el **mismo Excel del libro que sale de ②**, con el núcleo v1.9.1 tal cual. Nada sale de su PC.
- **Top 3 Musts:** R1 crudo → Excel idéntico · R2 extracto repartido por día como en la app · R3 cero datos salen del navegador.
- **NFR clave:** S1–S6 (sitio estático expuesto: CSP estricta, todo auto-alojado y fijado, archivos subidos = no confiables) + mismo cálculo que la app (ADR-002).
- Meta práctica (STATE): que el contador lo pruebe pronto con el crudo de sept. 2026; se recorta alcance para llegar ahí.

## Stories
- **R1 (Must)** Como contador, quiero subir un crudo .json y descargar el Excel del libro, para tener los asientos sin instalar la app.
  - Dado el crudo real de sept. 2026 (v1.9.1), cuando lo subo y pulso «Generar Excel», entonces descargo `reporte_contable_<AAAAMMDD>.xlsx` con las 5 hojas y 0 celdas distintas (valor y formato) frente a `cont_excel` de v1.9.1 con los mismos datos y la misma config.
  - Dado un crudo con `version` ≠ 1, sha256 que no coincide, JSON roto o demasiado anidado, entonces no se genera nada y sale un mensaje en español con el motivo (sin traza de Python).
- **R2 (Must)** Como contador, quiero subir el extracto .xlsx junto al crudo, para que las líneas del banco entren al libro como en la app.
  - Dado crudo + extracto de sept., entonces el Excel es igual al de la app tras «subir extracto» con el mismo crudo, las mismas reglas (`extracto_reglas.json` v1.9.1) y memoria vacía.
  - Dado un extracto > 5 MB o que no es de Bancolombia, entonces se rechaza con el motivo y el crudo sigue cargado.
  - Las líneas que caen en días que el crudo no trae crean ese día (igual que `cont_extracto`).
- **R3 (Must)** Como dueño de los datos, quiero que ningún archivo ni valor salga del PC del contador, para cumplir «todo local».
  - Dada la página cargada, cuando genero el Excel, entonces la pestaña Red muestra solo GET al mismo origen de archivos estáticos (cero POST, cero otros hosts), y la CSP bloquea cualquier intento.
  - No hay login, cookies, analítica ni formularios que envíen datos.
- **R4 (Must)** Como contador, quiero poner negocio y NIT una vez, para que salgan en el encabezado del Excel.
  - Dado que escribo negocio y NIT, entonces salen en el Excel; al volver a abrir la página en el mismo navegador siguen ahí (almacenamiento local; si falla, la página igual funciona y los pide de nuevo).
- **R5 (Must)** Como usuario, quiero que cada versión nueva de la página siga leyendo crudos v1, para que el contador no dependa de mi versión de captura.
  - Test automático: el crudo de v1.9.1 (fijado en el repo, sin datos reales o con datos de prueba) produce el Excel esperado en la página de la versión nueva; si no, el despliegue no sale.
- **R6 (Must)** Como contador, quiero abrir siempre la misma dirección para una versión, para saber qué cálculo usé.
  - Cada tag `vX.Y.Z` publica una URL que no cambia; la página muestra su versión y la del núcleo.
- **R7 (Should)** Como contador, quiero ver el avance mientras carga (~14 MB la 1ª vez) y calcula, para saber que no se colgó.
  - Mensajes «Cargando motor… / Leyendo crudo… / Armando libro… / Listo»; si un día del crudo es inválido, se lista con su motivo y el resto sigue (R10 de ADR-004).
- **R8 (Should)** Como contador, quiero poder cargar la memoria del extracto (destinos aprendidos), para que las líneas enseñadas en la app no queden «por revisar».
  - Dado el archivo de memoria exportado de la captura, entonces el Excel con crudo + extracto + memoria = el de la app. Sin archivo, R2 vale con memoria vacía.
- **R9 (Could)** Subir varios crudos (p. ej. dos quincenas) y armar un solo Excel; días repetidos e iguales se omiten, distintos se listan como conflicto (regla de ADR-004).

## Non-functional
- **Consistencia:** generar Excel = determinista, mismo resultado que CPython (ADR-002); la página no tiene estado de servidor.
- **Latencia (PC del contador, Chrome/Edge escritorio):** 1ª carga ≤ 30 s con 10 Mbps; cargas siguientes ≤ 5 s (caché); generar un mes ≤ 10 s; la página no se congela (Pyodide en Web Worker).
- **Navegadores:** Chrome y Edge actuales de escritorio = soportados; Firefox = debería; Safari y móvil = sin garantía (aviso si falla).
- **Costo:** Netlify gratis; ~15 MB por versión.
- **S1 (sin secretos ni datos reales en el bundle):** el sitio no lleva `terceros_cuentas.json`, `por_confirmar.json` real, libro, NIT ni claves; el build falla si los encuentra.
- **S2 (entradas no confiables):** topes antes de parsear (crudo ≤ 20 MB, extracto ≤ 5 MB, topes de ADR-004 por valor/texto/anidado/documentos); formato/versión desconocidos se rechazan; los archivos se leen solo como datos, nunca se ejecutan (`runPython` solo con código fijo del sitio).
- **S3 (sin salidas):** sin fetch a URLs del usuario; `connect-src 'self'`; nada de micropip/PyPI ni CDN en runtime.
- **S4 (cabeceras):** CSP de 01 (`default-src 'none'; script-src 'self' 'wasm-unsafe-eval'; worker-src 'self' blob:; connect-src 'self'; img-src 'self' blob: data:; style-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'`) + `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `Permissions-Policy` vacía; HTTPS; snippet injection y analítica de Netlify apagadas; errores genéricos (detalle técnico plegado, sin rutas locales).
- **S5 (dependencias fijadas):** Pyodide 314.0.7, openpyxl 3.1.5, et_xmlfile 2.0.0 auto-alojados con sha256 verificado en el build; lockfile en el repo.
- **S6 (N/A justificado):** sin BD, sin authz, sin rate limits: no hay backend.
- **Regulated:** no entra ningún valor legal nuevo. Los del núcleo (catálogo PUC — Decreto 2650/1993; reglas del extracto y GMF 4×1000 — art. 871 ET; cuentas por confirmar de ADR-022) viajan **fijados por versión**; cambian solo con un tag nuevo, tras confirmación del contador.

## Out of scope
- Vendty (hasta tener factura de ejemplo + API), documento soporte (se queda en la captura), OCR.
- Corregir o reclasificar cuentas en la página (el contador corrige en el Excel), «Reclasificar mes», enseñar al motor.
- Alertas «cambió desde que se confirmó» (el crudo v1 no trae débito/crédito guardados) → hoja de alertas vacía; ver Q3.
- Login, servidor, guardar archivos en la nube, móvil/Safari garantizados.

## Decisions (usuario 2026-10-26, aprobado)
- Q1 → negocio/NIT: campos en la página, recordados en el navegador (R4 tal cual).
- Q2 → memoria del extracto: Should, después del primer uso del contador (R8).
- Q3 → alertas «cambió»: fuera de este ciclo.
