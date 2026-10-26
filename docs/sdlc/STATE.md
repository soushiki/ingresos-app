# SDLC state

project: ingresos_app · Modo contador web (Pyodide, todo local)
goal: una página estática en Netlify (URL fija por versión) donde el contador sube el crudo de la captura (ADR-004) y el extracto del banco (sin Vendty), y su navegador arma y descarga el Excel del libro con el mismo núcleo contable, sin que ningún dato salga de su PC
size: M  # entrega nueva (núcleo en Pyodide, página estática, despliegue por tag, test de compatibilidad del crudo); sin lógica contable nueva
exposed: yes  # sitio web público (estático, sin backend): CSP, dependencias de CDN fijadas, archivos subidos = no confiables
regulated: yes  # genera asientos PUC para los libros y la renta (misma lógica que la app)
next: 5-implement
current task: T4 (`web_build.py` mínimo + `web.lock` + `probar_web.py`)
priority: **PRIORIDAD (usuario 2026-10-26): terminar este ciclo antes que M-18/M-19/Marcador.** Meta práctica: que el contador lo pruebe pronto con crudos ya producidos (sept. 2026 del libro actual) y vea cómo funciona; cortar alcance si hace falta para llegar ahí rápido.

## Stages
- [x] 0-triage
- [x] 1-research  (spike PASS: Excel idéntico en Pyodide)
- [x] 2-requirements
- [x] 3-design
- [x] 4-plan
- [ ] 5-implement
- [ ] 6-test
- [ ] 7-release

## Ciclos anteriores
- Documento soporte, precisión OCR v1.1.0, recibos omitidos v1.2.0, cierre de caja v1.3.0 + v1.3.1, Rappi v1.4.0, medio de pago v1.5.0, extracto bancario v1.6.0, Indra OCR v1.7.0, cuenta PUC v1.8.0, recuperar número v1.9.0 → `archive/<ciclo>/`.
- Siguen en su sitio: `01b`…`01h` (ignorados), `08-maintenance.md`, `adr/`.

## Pendientes
- Contador (no bloquea): contestar `docs/por-confirmar-contador.pdf` (8 decisiones + 5 alias; la 4 ya tiene la mitad del recibo de agua). Al llegar: editar `por_confirmar.json` («estado»: «confirmado», cuenta/alias) y «Reclasificar mes» de cada mes ya guardado.
- Usuario: smoke de v1.6.0 (`archive/extracto/06-test-report.md`), avisar al contador del recálculo de sept. 1–23 y de las cuentas «por confirmar»; borrar la rama local `respaldo/antes-limpieza-v1.6.0` cuando ya no haga falta.
- Usuario: re-subir fotos Rappi de sept. (`archive/rappi/07-release.md`), actualizar los PC a v1.9.0, smoke de v1.3.x y v1.5.0 (pasos 1–3 en `archive/medio-de-pago/07-release.md`).
- POS Ascomp → Vendty (≈ nov. 2026): antes del cambio, preguntar a Ascomp (ascompos@hotmail.com, 3108094441, WhatsApp +57 320 4451364) si exporta ventas pasadas a Excel/CSV. Cuando arranque: fecha exacta, foto de un recibo Vendty, documentación de su «Api de integración» y si el plan la incluye → posible ciclo «importar ventas Vendty» (S–M). Preguntar al contador por qué se pasó a POS electrónico (afecta M-18).
- **EN CURSO, prioridad 1** (2026-10-26, pedido del usuario): **modo contador web (M)** — captura (OCR, tu PC) exporta crudo (ADR-004); el contador abre una página estática en Netlify (una URL fija por tag) donde el núcleo contable corre en su navegador (Pyodide): sube crudo / extracto / Vendty y **solo genera y descarga el Excel**. Decidido por el usuario 2026-10-26: **todo local**, nada se sube ni se guarda en un servidor; sin login. Su memoria (alias, reclasificaciones, terceros) = archivo que carga/descarga o almacenamiento del navegador. Crudo v1 = contrato público: versiones nuevas siguen leyendo v1 + test con un crudo de v1.9.1. Primero un spike (≈ horas): núcleo + openpyxl en Pyodide generan el Excel con un crudo real.
- Candidatos a ciclo (después del modo contador web): Marcador de renta (`docs/marcador-renta.html`) M-18 perfil fiscal (S) → M-19 NIT por tercero (S–M) → M-20 soporte por gasto + efectivo 771-5 (S) → M-21 impoconsumo bimestral (S) → M-22 pestaña Marcador (M) → M-23 cruce con facturas DIAN (M) → M-24 paquete de cierre (M). Antes de M-18: confirmar con el contador régimen, impoconsumo, ICA y saldos iniciales → hoja `docs/preguntas-contador-perfil-fiscal.pdf` (9 preguntas, 2026-10-26), por enviar. Deuda chica: 2 notas de M-27 It. 3 en 08.
- Chequeo mensual (08): 2026-11-17.

## Log
(log del ciclo #8 recuperar número → archive/recuperar-numero/STATE.md)
2026-10-26 | 8-maintain | M-26 cerrado (v1.9.0); ciclo → archive/recuperar-numero/ (02, 04, 06, 07, STATE); 08 al día (resumen v1.9.0, fila M-26 cerrada); falta smoke del usuario; próximo ciclo por elegir (M-18 tras confirmar con el contador, o Vendty cuando llegue)
2026-10-26 | 8-maintain | smoke v1.9.0 PASS (usuario + captura): 85334 y 85375 recuperados con número correcto, «dudosos» con motivo «Número recuperado…», sin «Falta 85334»; 85340 (486.990) va «dudoso». Nuevos: M-29 cola de fotos (cerrado, f688232), M-30 textos de ④ (XS, abierto)
2026-10-26 | 7-release | v1.9.1 preparada (M-29, M-30, M-31, M-32): suite verde, 127.0.0.1, sin migración; VERSION + CHANGELOG; commit local → esperando OK para push main + tag
2026-10-26 | 7-release | v1.9.1 publicada: push main + tag (e6a0a7a..7183832); la hoja de M-18 se sacó del historial antes del push (sin versionar, como los otros PDF del contador; rama local backup/antes-sacar-hoja-m18 la conserva) → next 0-triage
2026-10-26 | 0-triage | borrador modo contador web: meta (página Netlify, núcleo en Pyodide, crudo + extracto → Excel, todo local), M, exposed yes (estático), regulated yes; alternativa barata: tú exportas el Excel en ② y se lo mandas (ya funciona hoy) → esperando confirmación + 3 preguntas
2026-10-26 | 0-triage | confirmado por el usuario: meta y tamaño M; (1) el Excel = el mismo libro que sale hoy de ②, el documento soporte se queda en la app de captura; (2) el contador no corrige cuentas en la página, solo en el Excel si quiere; (3) Vendty fuera hasta tener un ejemplo de factura y la API pedida a soporte → next 1-research
2026-10-26 | 0-triage | usuario: el modo contador web es prioridad; terminarlo primero para que el contador lo pruebe con crudos ya producidos (sept.)
2026-10-26 | 1-research | spike PASS: núcleo tal cual en Pyodide 314.0.7 + openpyxl local; crudo sept. → Excel idéntico a CPython (25.902 celdas, 0 dif.), extracto igual; carga 1 s + cálculo 2,1 s, 14 MB; falta probar CSP/Worker en navegador → 01-research.md, spikes/pyodide/ → next 2-requirements
2026-10-26 | 2-requirements | borrador 02: R1–R6 Must (crudo→Excel idéntico, extracto, nada sale, negocio/NIT, crudo v1, URL por versión), R7–R8 Should, R9 Could; S1–S6; 3 preguntas → esperando aprobación (gate)
2026-10-26 | 2-requirements | aprobado por el usuario con Q1–Q3 recomendadas (NIT en la página, memoria extracto = Should, alertas fuera) → next 3-design
2026-10-26 | 3-design | borrador 03 + ADR-026 (libro.py compartido app/página), ADR-027 (subcarpeta /vX.Y.Z/ inmutable, deploy CLI desde el PC), ADR-028 (lista blanca, Worker, CSP); riesgo 1 = spike T1 CSP en Chrome → esperando aprobación (gate)
2026-10-26 | 3-design | aprobado por el usuario (03 + ADR-026/027/028 aceptados) → next 4-plan
2026-10-26 | 4-plan | 04-plan: 3 iteraciones, 14 tareas, ≈ 15 h; It. 1 (T1–T7, ≈ 6 h) termina en URL borrador con el Excel de sept. para el contador → next 5-implement (T1)
2026-10-26 | 5-implement | T1 PASS: Pyodide 314.0.7 en Worker módulo + openpyxl con la CSP exacta de S4 en Chrome 156, Edge 156 y el panel; eval/fetch externo bloqueados en el Worker; ADR-028 sin cambios (solo nota favicon) → T2
2026-10-26 | 5-implement | T2 PASS: `parser_module/contable/libro.py` (cfg, dia, dia_desde_crudo, desde_crudo, facturas_cerca/usadas, recalcular_dia, aplicar_extracto, excel); app.py lo llama (−63 líneas); suite completa idéntica antes/después → T3
2026-10-26 | 5-implement | T3 PASS: `libro.generar` + `EntradaInvalida` (topes 20/5/1 MB, negocio/NIT sin fórmula, memoria validada, `ahora` inyectado); `probar_libro.py` 0 celdas distintas vs app (crudo y crudo + extracto) + 31 ataques; `web/pruebas/datos/crudo_v1.json` sintético fijo (R5); suite verde → T4
