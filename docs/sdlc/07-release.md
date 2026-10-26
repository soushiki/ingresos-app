# 07 · Release — ingresos_app (ciclo M-27 cuenta PUC por origen e ítem)

## Runbook
App Flask local (127.0.0.1, `exposed: no`). No hay servidor: «desplegar» = llevar `main` a cada PC y reiniciar la app.
Hay dos instalaciones: **tu PC** (con Ollama, lee fotos) y **el PC del contador** (`SIN_OCR=1`, importa el .json crudo).

**Build / instalación** (primera vez en un PC; el detalle para el contador está en `LEEME-contador.md`)
1. Python 3 con PATH. `git clone` (o copia sin `datos/`).
2. `pip install -r requirements.txt`
3. `.env` copiado de `.env.example` y llenado.
4. `iniciar.bat` → abre http://127.0.0.1:5050

**Entorno (.env, solo nombres)**: `PORT` (5050), `NO_BROWSER`, `SIN_OCR` (1 en el PC del contador),
`LOCAL_VLM_URL`, `LOCAL_VLM_MODEL`, `LOCAL_VLM_KEY`, `GEMINI_API_KEY` / `GOOGLE_API_KEY`, `GEMINI_MODEL`, `TESSERACT_LANG`.
Motores locales (solo tu PC): Ollama con qwen2.5vl, Indra OCR (desde 1.7.0: R3 + enderezado, en `indra_venv` con Python 3.14; si falta, Tesseract con banda de aviso), Tesseract (respaldo de R3; si falta, se salta con aviso), Real-ESRGAN opcional (V4).
Variables opcionales de Indra (solo nombres): `INDRA_VENV`, `INDRA_HILOS`, `INDRA_TIMEOUT_S`, `INDRA_ARRANQUE_S`.
**Indra, primera vez en tu PC** (no en el del contador): `winget install Python.Python.3.14` → `instalar_indra.bat` (se puede repetir; termina en «Indra listo»; baja los modelos una sola vez y luego funciona sin red) → `python probar_indra.py` → «OK: 0 fallos».
Datos fuera de git: `datos/` (libro.json, soporte.db, catalogo.json, recortes/, referencia), `parser_module/contable/terceros_cuentas.json`, `*.xlsx`.

**Publicar una versión** (desde tu PC)
1. Suite verde (26 suites; `probar_imagen.py` es manual y `probar_motores_falso.py` es el trabajador falso): `for f in probar_*.py; do case $f in probar_imagen.py|probar_motores_falso.py) continue;; esac; printf "$f: "; python $f | tail -1; done`
2. `VERSION` + entrada en `CHANGELOG.md`; commit.
3. `git checkout main && git merge --no-ff <rama> && git tag vX.Y.Z && git push origin main --tags`

**Actualizar un PC** (tuyo o del contador)
1. Cerrar la app. **Copia de `datos/`** (sobre todo `datos/soporte.db`: la numeración CTG/NA no se puede rehacer).
2. `git pull` (o copiar los archivos nuevos sin tocar `datos/`) → `pip install -r requirements.txt`.
3. `iniciar.bat`. soporte.db migra solo (`user_version`).

**Health check**: la página abre en :5050; `GET /api/estado` responde (en el contador, `sin_ocr: true`);
la pestaña ③ muestra las mismas semanas que antes de actualizar; desde 1.1.0, ④ Revisión lista los dudosos y abre un recorte; desde 1.2.0, ④ → «Faltan» lista los marcadores; desde 1.3.0, un día con cierre en ③ muestra las filas «según cierre» y débito = crédito; desde 1.4.0, un día con papel de Rappi muestra una fila 13452501 (tercero Rappi, medio App) con el ID en «Ordenes»; desde 1.5.0, ③ y DATOS OCR solo muestran los 8 medios (o vacío) y DATOS OCR trae «Medio según el papel»; desde 1.6.0, ⑤ «Extracto» abre y lista «Importaciones» y «Por revisar»; desde 1.7.0, `GET /api/contable/capacidades` trae `motor: "indra"` y `aviso: null` (en el contador o sin `indra_venv`: `motor: "tesseract"` y la banda de aviso visible), y una foto subida en ① deja un `python` de `indra_venv` en `tasklist` que desaparece ≤ 5 s después de cerrar la app; desde 1.8.0, un papel de compra en ③ muestra «Cuenta por ítem» con capa y motivo, y «Reclasificar mes» con 2026-09 dice que no hay cambios (sept. ya está reclasificado).

**Rollback**: cerrar la app → `git checkout vX.Y.Z-anterior` → restaurar la copia de `datos/` hecha en el paso 1
(obligatorio si la versión nueva migró soporte.db: la versión vieja no conoce las migraciones nuevas).
1.2.0 no migra soporte.db, pero escribe marcadores `tipo: "faltante"` en libro.json; la 1.1.0 no los conoce → restaurar la copia de `datos/`.
1.3.0 no migra soporte.db; reescribe los asientos de los días con cierre al recalcular. Volver a 1.2.0: `git checkout v1.2.0` y copiar
`datos/libro.antes-v1.3.0.json` sobre `datos/libro.json` (o la copia de `datos/` del paso 1).
1.4.0 no migra soporte.db. Volver a 1.3.1: `git checkout v1.3.1` y copiar `datos/libro.antes-v1.4.0.json` sobre `datos/libro.json`.
1.5.0 no migra soporte.db. Volver a 1.4.0: `git checkout v1.4.0` y copiar `datos/libro.antes-v1.5.0.json` sobre `datos/libro.json`.
1.6.0 no migra soporte.db. Primero, si basta, ⑤ → «Deshacer» cada importación. Volver a 1.5.0: `git checkout v1.5.0` y copiar `datos/libro.antes-v1.6.0.json` sobre `datos/libro.json`; borrar `datos/extracto_memoria.json`.
1.7.0 no migra soporte.db ni recalcula el libro. Volver a 1.6.0: `git checkout v1.6.0` (sin restaurar `datos/`). Sin cambiar de versión: renombrar `indra_venv\` → la app vuelve a Tesseract sola.
1.8.0 no migra soporte.db. Volver a 1.7.0: `git checkout v1.7.0` y copiar `datos/libro.antes-v1.8.0.json` sobre `datos/libro.json` (se crea la primera vez que se aplica «Reclasificar mes»; en tu PC ya existe). Para deshacer solo la reclasificación de sept., usa `datos/libro.backup-antes-reclasificar-sept.json`. Ojo: también deshace la respuesta del contador que ya se aplicó.

**Después de actualizar a 1.8.0**: en tu PC no hay que hacer nada, porque sept. ya está reclasificado y la decisión 4 ya está aplicada. En el PC del contador: copia de `datos/`, luego importa el .json nuevo. `terceros_cuentas.json` no viaja con git; sin él, la capa proveedor usa el `.example` y van más ítems a la puente. Cuando el contador conteste `docs/por-confirmar-contador.pdf`: edita `por_confirmar.json` («estado»: «confirmado») y usa «Reclasificar mes» en cada mes guardado; revisa la vista previa antes de Aplicar.
`requirements-entrenar.txt` (sklearn) no hace falta: el spike T5d quedó solo como registro (ADR-025).

**Después de actualizar a 1.6.0 (antes de la primera importación)**: copia de `datos/libro.json`. Avisarle al contador: importar recalcula los días tocados y los guardados antes de v1.3.0 (sept. 1–23) toman las reglas de cierre: aparecen filas 13809501 y 2815xx y cambia el débito del día. Lo cambia el recálculo, no el extracto. Las cuentas de `extracto_reglas.json` siguen «por confirmar» con el contador.

**Después de actualizar a 1.5.0**: recalcular los meses abiertos (③) y volver a exportar el Excel; no hay que re-subir fotos.

**Después de actualizar a 1.4.0 (solo tu PC, con OCR)**: los papeles de Rappi ya guardados no tienen `rappi` y recalcular no los arregla.
En ① volver a subir, día por día, las fotos de comandas que traen papel de Rappi (nombre con «rappi», p. ej. días 2, 3, 5, 6, 7 y 11 de sept.)
y recalcular el mes; revisar en ③ las filas 13452501 y en ④ los que queden con aviso «No se leyó el total de Rappi».
Al primer guardado se crea `datos/libro.antes-v1.4.0.json`. En el PC del contador: importar el .json nuevo después.

**Licencia de Indra (R8, leída 2026-10-24)**: el código es Apache-2.0. Los pesos son una «AI Pubs Open RAIL-M (Modified) v0.1», con copia en `docs/licencias/indra-ocr-pesos-LICENSE.txt`. Uso gratis salvo en estos casos: más de US$20 M de ingresos el año anterior, más de US$20 M de financiación, u ofrecer algo que compita con Datalab (Anexo A §2). El negocio cumple. No se redistribuyen los pesos: `indra_venv/` y la caché de HF quedan fuera de git, y cada PC los baja, así que §4 no aplica. Hay que dar crédito y enlace (§7): está en README «Indra». El §8 extiende la licencia a la salida, y entrenar otro modelo con esa salida cuenta como derivado (def. e). Por eso los pares de `exportar_entrenamiento` no deben usarse para entrenar ni ajustar un modelo si sus etiquetas vienen de Indra, salvo que ese modelo quede bajo la misma licencia. Hay que volver a revisarla si la app se vende, se ofrece a otros como servicio o se cambia de versión de los pesos (§9: Datalab puede actualizarlos).
**CI**: no hay. Sugerido (GitHub Actions, Windows): la suite de arriba + gitleaks (historial completo) + `pip-audit`
+ `bandit -r . -x ./datos`. Hoy no están instalados localmente; pre-flight hecho con grep (ver Releases).
**Logs**: Flask no registra cuerpos; cédulas/NIT solo viven en soporte.db y en los Excel.
**Monitoreo RED**: no aplica (un usuario, local). Línea base de calidad: `python medir_precision.py --completo --peores 20 --de-cero` (103 recibos de sept.; informe 20261019-135040: omitidos 5, validados con error 7, dudosos 27; ≈ 4 h, reanudable). Con Indra (1.7.0, informe 20261020-225729): omitidos 5, validados con error 7, dudosos 26.
**Repo público**: nada con cifras reales, nombres de terceros ni datos del negocio (01b/01c/01e/01f/01g, nombre/dirección del local) entra a `main` ni a `origin`. Los casos reales que una prueba necesita van junto a los datos reales (`../data/`), no en el test.

## Releases
2026-10-25 | v1.8.0 | **Commit listo; tag y push pendientes (esperando OK)**: cuenta PUC por origen e ítem (M-27, T1–T12 + FIX-1…3 + DEBT-2 + decisión 4). Pre-flight OK: suite 26/26, debug off, solo 127.0.0.1, sin migración; N1 igual tras limpiar (67,2 % por ítem, 87,3 % precisión). Limpieza: `minar_manual.py` detecta personas por nombre de pila sin marca de empresa → 4 terceros persona y 1 vecino salen de `modelo_manual.json` a `terceros_cuentas.json` (local); historial sin publicar (origin/main 550c5ad..main, 32 commits) reescrito con filter-branch (solo cambia ese archivo); `ejemplos.py` con nombre inventado. Rama local `respaldo/antes-limpieza-v1.8.0` con los nombres: no se publica, borrar cuando no haga falta. No se publican los PDF/HTML de `docs/` para el contador.
2026-10-24 | v1.7.0 | **Publicada**: push main + tag v1.7.0 (387f910..c7c95b0): Indra OCR (M-25, T1–T10). Pre-flight OK: suite 22/22, sin claves en v1.6.0..HEAD, debug off, solo 127.0.0.1, sin migración ni recálculo (VERSION_RESPALDO = 1.6.0). R8 leída (ver Runbook). Falta: smoke manual de 06 I3 (4 pasos) y no hay Indra en el PC del contador (no hace falta). Meta ≤ 2/103 omitidos no alcanzada → M-26.
2026-10-20 | v1.6.0 | **Publicada**: push main + tag v1.6.0: extracto bancario (01c #5, T1–T13 + FIX-1..3). Pre-flight OK: suite 20/20, debug off, solo 127.0.0.1, sin claves, sin migración de soporte.db; VERSION_RESPALDO = 1.6.0. Cifras reales y nombres de terceros movidos a `01g-cifras-extracto.md` (ignorado); los casos reales del oráculo MOVIMIENTOS viven en `../data/extracto_oraculo.json`; pruebas con nombres y valores falsos; historial sin publicar reescrito (filter-branch) antes del push. Rama local `respaldo/antes-limpieza-v1.6.0` (con datos reales: no se publica; borrar cuando ya no haga falta). Falta (usuario): smoke de 06, avisar al contador y actualizar los PC.
2026-10-20 | v1.5.0 | **Publicada**: push main + tag (550907b..c7da075): vocabulario de medio de pago (01c #8, T1–T4 + FIX-1). Pre-flight OK: suite 19/19, sin claves ni cifras reales en v1.4.0..HEAD (valores de prueba falsos), debug off, solo 127.0.0.1, sin migración de soporte.db; VERSION_RESPALDO = 1.5.0. Falta (usuario): smoke manual 1–3 de 06, recalcular meses abiertos y actualizar los PC.
2026-10-19 | v1.4.0 | **Tag local; push pendiente** (sin red a github.com desde la sesión): Rappi (01c #6). Pre-flight OK: suite 18/18, sin claves en v1.3.1..HEAD, debug off, solo 127.0.0.1, sin migración de soporte.db. Cifras reales del ciclo (IDs, valores, 13452501 sept.) → `01f-cifras-rappi.md` (ignorado); pruebas con valores falsos; historial sin publicar reescrito antes del push. Ya públicos de antes (08 #6): ID/valor del 17-09 y el «2,4 M». Falta (usuario): re-subir fotos Rappi de sept. (runbook) y actualizar los PC.
2026-10-19 | v1.3.1 | **Publicada**: M-17 (ajuste R1 como fórmula, helper `consumo_papeles`). Pre-flight OK: suite 18/18, sin claves ni cifras nuevas en v1.3.0..HEAD, sin migración de soporte.db. Rollback a v1.3.0: `git checkout v1.3.0` y volver a exportar el Excel. Falta (usuario): smoke de v1.3.0 + actualizar los PC.
2026-10-19 | v1.3.0 | **Publicada**: tag v1.3.0, push main + tags. Pre-flight OK: suite 18/18, sin claves en v1.2.0..HEAD, debug off, solo 127.0.0.1, sin migración de soporte.db. Cifras reales del ciclo movidas a `01e-cifras-cierre.md` (ignorado) e historial sin publicar reescrito antes del push. Falta (usuario): smoke de 06 y actualizar los PC (runbook).
2026-10-19 | v1.2.0 | **Publicada**: tag v1.2.0, push main + tags (88e61a5..94b7173). Pre-flight OK: suite 18/18, sin claves ni nombre/dirección del local en v1.1.0..HEAD, debug off, solo 127.0.0.1, sin migración de soporte.db. Falta (usuario): actualizar los PC (runbook) y abrir ④ → «Faltan».
2026-10-18 | v1.1.0 | Publicada (ver archive/precision-ocr/07-release.md).
2026-10-17 | v1.0.1 | Publicada (M-1..M-3).
2026-10-17 | v1.0.0 | Publicada.
