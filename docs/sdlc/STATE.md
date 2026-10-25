# SDLC state

project: ingresos_app · Indra OCR (M-25)
goal: Indra OCR pasa a ser el segundo lector R3 (en lugar de Tesseract-dígitos) y el enderezador de fotos, local en su propio venv 3.14, para bajar omitidos de 5/103 a ≤ 2/103 sin empeorar totales; sin Indra vuelve a Tesseract (v1.6.0) y avisa; script de instalación (venv + indra-ocr==1.1.2 + modelo una vez, luego offline)
size: M  # dos piezas (lector R3 + enderezado) + proceso trabajador en otro venv + instalador; evidencia ya existe (spike e6e46e2)
exposed: no  # app Flask local en 127.0.0.1
regulated: no  # OCR, no cifras fiscales; licencia pesos OpenRAIL-M modificada: gratis bajo US$20 M de ingresos → aplica
next: 7-release
current task: — (I3 completa)

## Stages
- [x] 0-triage
- [x] 1-research  (ligera: partir de docs/ocr-indra-comparison.md)
- [x] 2-requirements
- [x] 3-design
- [x] 4-plan
- [x] 5-implement
- [x] 6-test
- [ ] 7-release
- [ ] 8-maintain

## Ciclos anteriores
- Documento soporte, precisión OCR v1.1.0, recibos omitidos v1.2.0, cierre de caja v1.3.0 + v1.3.1, Rappi v1.4.0, medio de pago v1.5.0, extracto bancario v1.6.0 → `archive/<ciclo>/`.
- Siguen en su sitio: `01b`, `01c`, `01d`, `01e`, `01f`, `01g` (ignorados), `08-maintenance.md`, `adr/`.

## Pendientes
- Usuario: smoke de v1.6.0 (`archive/extracto/06-test-report.md`), avisar al contador del recálculo de sept. 1–23 y de las cuentas «por confirmar»; borrar la rama local `respaldo/antes-limpieza-v1.6.0` cuando ya no haga falta.
- Usuario: re-subir fotos Rappi de sept. (runbook en `archive/rappi/07-release.md`), actualizar los PC a v1.6.0, smoke de v1.3.x y v1.5.0 (pasos 1–3 en `archive/medio-de-pago/07-release.md`).
- Nuevo (2026-10-20): el POS es Ascomp; pasa a Vendty el mes que viene (≈ nov. 2026, aún no instalado), así que todo lo de hoy es Ascomp y M-25 sigue igual. Antes del cambio: preguntar a Ascomp (ascompos@hotmail.com, 3108094441, WhatsApp +57 320 4451364; tiene login en nube.ascomp-pos.com) si se pueden exportar las ventas pasadas a Excel/CSV; su web no documenta informes ni formato del recibo. Cuando arranque: fecha exacta, una foto de un recibo Vendty y pedir a Vendty la documentación de su «Api de integración» (sí existe, está en su web) y si el plan la incluye; con API o export Excel/CSV, posible ciclo «importar ventas Vendty» (S–M) en vez de OCR para los días nuevos. Abecé DIAN (feb. 2025): el tiquete POS es documento equivalente que la DIAN valida; persona natural no responsable de IVA/INC no está obligada salvo > 3.500 UVT → preguntar al contador por qué se pasó a POS electrónico (afecta M-18).
- Candidatos a ciclo: **M-25 Indra OCR (M, absorbe M-16)** — segundo lector R3 + orientación/enderezado, venv 3.14 aparte, licencia OpenRAIL-M. Marcador de renta (`docs/marcador-renta.html`) M-18 perfil fiscal (S) → M-19 NIT por tercero (S–M) → M-20 soporte por gasto + efectivo 771-5 (S) → M-21 impoconsumo bimestral (S) → M-22 pestaña Marcador (M) → M-23 cruce con facturas DIAN (M) → M-24 paquete de cierre (M). Antes de M-18: confirmar con el contador régimen, impoconsumo, ICA y saldos iniciales.

## Log
(log del ciclo #5 → archive/extracto/STATE.md)
2026-10-20 | 8-maintain | #5 cerrado (v1.6.0); ciclo → archive/extracto/ (01–04, 06, 07, STATE); 08 al día; M-25 Indra OCR anotado (absorbe M-16); chequeo mensual 2026-11-17; falta elegir el próximo ciclo (M-25 recomendado o M-18)
2026-10-20 | 8-maintain | usuario elige próximo ciclo: M-25 Indra OCR → next 0-triage
2026-10-20 | 0-triage | M-25 Indra OCR: meta confirmada (lector R3 + enderezado), M, exposed no, regulated no; respaldo Tesseract; script de instalación → next 1-research (ligera)
2026-10-20 | 1-research | ligera: onnxruntime sin cp315 → trabajador 3.14 por JSON-líneas (ready, timeout+reinicio, candado); fijar indra-ocr 1.1.2; enganches leer_digitos/giro_automatico; 8 riesgos (meta omitidos sin medir, 3 dudosos falsos, upright no documentado) → next 2-requirements
2026-10-20 | 2-requirements | aprobado: 8 historias (R1–R4, R6 Must; R5, R7, R8 Should), N1–N6; Q1 regla dudoso igual, Q2 instalador solo avisa sin py 3.14, Q3 ≤2 omitidos es Should → next 3-design
2026-10-20 | 3-design | borrador: trabajador persistente (ADR-016), fachada motores con respaldo (ADR-017), giro+inclinación aplicados en la app (ADR-018); spike XS de fondo blanco al empezar 5 → esperando aprobación
2026-10-20 | 3-design | aprobado por el usuario; ADR-016–018 aceptados → next 4-plan
2026-10-20 | 4-plan | 3 iteraciones, 10 tareas (≈ 11 h): I1 trabajador+cliente+fachada+R3 conectado (ADR-016/017 con trabajador falso), I2 spike fondo blanco+enderezado+aviso+instalador, I3 probar_indra+R5 → next 5-implement (T1)
2026-10-20 | 5-implement | T1 hecho (Sonnet): ocr_module/indra_worker.py — ready/numeros/upright/quit/EOF/{"error"}; probado a mano en el venv del spike → next T2
2026-10-20 | 5-implement | T2 hecho (Opus): ocr_module/indra.py cliente + probar_motores.py (30 ✓) + probar_motores_falso.py; humo real pendiente (sin venv) → next T3
2026-10-20 | 5-implement | T3 hecho (Sonnet): ocr_module/motores.py fachada (leer_digitos, detectar_giro, estado+aviso); +16 en probar_motores.py; todos los probar_*.py OK → next T4
2026-10-20 | 5-implement | contexto nuevo: POS Ascomp → Vendty; web de Vendty: POS electrónico DIAN, informes por correo, Siigo y «Api de integración» (corregido: el usuario la mostró); sin documentación pública → T4 en espera de respuestas del usuario
2026-10-20 | 5-implement | Vendty no está instalado: llega ≈ nov. 2026; fotos actuales = Ascomp → M-25 sigue, T4 sale de espera
2026-10-20 | 5-implement | T4 hecho (Sonnet): app.py `_leer_hoja` y medir_precision `--completo` usan motores.leer_digitos; capacidades trae motor+aviso (sin venv: tesseract + «Indra no disponible…»); 21 probar_*.py OK; I1 completa → next 6-test (humo real con Indra espera a T8)
2026-10-20 | 6-test | I1 pasa: 21 probar_* OK; +1 check capacidades (motor/aviso) que faltaba; R1 numérico sin medir (sin venv → tras T8); menor: cerrar() sin plazo → anotado en T10 → next 5-implement (T5)
2026-10-20 | 5-implement | T5 hecho (Sonnet): spikes/indra_ocr/fondo.py; fondo blanco = replicar (residual 0,00° en 3 hojas × 8/25/45°, mismos recortes; medido por perfil de proyección, sin Indra) → línea en ADR-018 → next T6
2026-10-20 | 5-implement | T6 hecho (Opus): orientacion.enderezar + detectar en preparar_pagina/separar/_recortes; app.py y medir_precision --completo pasan motores.detectar_giro; 0° igual a v1.6.0 (fotos reales 42/43); +9 en probar_separar.py → next T7
2026-10-20 | 5-implement | T7 hecho (Sonnet): banda #aviso en contable.html (capacidades.aviso con textContent, cada 60 s; @media ancho+alto); verificado en el navegador: sin indra_venv se ve «Indra no disponible: se usa Tesseract», con aviso null se oculta; teléfono OK → next T8
2026-10-20 | 5-implement | T8 hecho (Sonnet): instalar_indra.bat + indra_requisitos.txt (freeze de venv nuevo py 3.14.8, indra-ocr 1.1.2) + .gitignore; dos corridas → «Indra listo»; motores.estado() = indra; fuera de lista: probar_documento_soporte.py salta carpetas *venv; 22 probar_* OK; I2 completa → next 6-test
2026-10-20 | 6-test | I2 pasa: 21 probar_* OK; R2 real por la app (20 hojas × 7 ángulos): 18 derechas + 2 de lado, incl ≤ 0,9°, ≤ 0,37 s/hoja, totales 101/107 en todo ángulo; 4 menores aceptados; R1/R3 con --completo en curso (≈ 4 h) → next 5-implement (T9)
2026-10-24 | 6-test | corrida completa con Indra (informe 20261020-225729): omitidos 5 → 5 (mismos), dudosos 27 → 26, validados con error 7 → 7 → R3 Must pasa; meta ≤ 2/103 (Should) no: R3 solo confirma → M-26 en 08
2026-10-24 | 5-implement | T9 hecho (Sonnet): probar_indra.py 6 ✓ con indra_venv (ready 1.1.2, numeros, upright 0/90, N5 repetibles); omitido limpio con INDRA_VENV inexistente; pista ADR-018 solo en fallos; probar_* OK → next T10
2026-10-24 | 5-implement | T10 hecho (Sonnet): Cliente.cerrar() acquire(1 s) y mata si hay pedido colgado; +2 en probar_motores.py (cierre colgado 1,0 s, app matada → EOF 0,1 s); nota README; tasklist sin python 3.14; arranque perezoso → un solo trabajador; 22 probar_* OK; I3 completa → next 6-test
2026-10-24 | 6-test | I3 pasa: 22 probar_* OK; R5 (cierre normal, colgado ≤ 3 s, app matada → EOF ≤ 5 s) y R7/N5 (probar_indra 6 ✓) cubiertos; 3 menores aceptados (_matar sin candado, giro 270 sintético, nota README doble); Musts R1–R4, R6 pasan; falta R8 → next 7-release
