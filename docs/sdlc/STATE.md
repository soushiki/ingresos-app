# SDLC state

project: ingresos_app · Indra OCR (M-25)
goal: Indra OCR pasa a ser el segundo lector R3 (en lugar de Tesseract-dígitos) y el enderezador de fotos, local en su propio venv 3.14, para bajar omitidos de 5/103 a ≤ 2/103 sin empeorar totales; sin Indra vuelve a Tesseract (v1.6.0) y avisa; script de instalación (venv + indra-ocr==1.1.2 + modelo una vez, luego offline)
size: M  # dos piezas (lector R3 + enderezado) + proceso trabajador en otro venv + instalador; evidencia ya existe (spike e6e46e2)
exposed: no  # app Flask local en 127.0.0.1
regulated: no  # OCR, no cifras fiscales; licencia pesos OpenRAIL-M modificada: gratis bajo US$20 M de ingresos → aplica
next: 5-implement
current task: T4

## Stages
- [x] 0-triage
- [x] 1-research  (ligera: partir de docs/ocr-indra-comparison.md)
- [x] 2-requirements
- [x] 3-design
- [x] 4-plan
- [ ] 5-implement
- [ ] 6-test
- [ ] 7-release
- [ ] 8-maintain

## Ciclos anteriores
- Documento soporte, precisión OCR v1.1.0, recibos omitidos v1.2.0, cierre de caja v1.3.0 + v1.3.1, Rappi v1.4.0, medio de pago v1.5.0, extracto bancario v1.6.0 → `archive/<ciclo>/`.
- Siguen en su sitio: `01b`, `01c`, `01d`, `01e`, `01f`, `01g` (ignorados), `08-maintenance.md`, `adr/`.

## Pendientes
- Usuario: smoke de v1.6.0 (`archive/extracto/06-test-report.md`), avisar al contador del recálculo de sept. 1–23 y de las cuentas «por confirmar»; borrar la rama local `respaldo/antes-limpieza-v1.6.0` cuando ya no haga falta.
- Usuario: re-subir fotos Rappi de sept. (runbook en `archive/rappi/07-release.md`), actualizar los PC a v1.6.0, smoke de v1.3.x y v1.5.0 (pasos 1–3 en `archive/medio-de-pago/07-release.md`).
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
