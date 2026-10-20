# 07 · Release — ingresos_app

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
Motores locales (solo tu PC): Ollama con qwen2.5vl, Tesseract (R3; si falta, se salta con aviso), Real-ESRGAN opcional (V4).
Datos fuera de git: `datos/` (libro.json, soporte.db, catalogo.json, recortes/, referencia), `parser_module/contable/terceros_cuentas.json`, `*.xlsx`.

**Publicar una versión** (desde tu PC)
1. Suite verde (18 suites; `probar_imagen.py` es manual): `for f in probar_*.py; do [ $f = probar_imagen.py ] || { printf "$f: "; python $f | tail -1; }; done`
2. `VERSION` + entrada en `CHANGELOG.md`; commit.
3. `git checkout main && git merge --no-ff <rama> && git tag vX.Y.Z && git push origin main --tags`

**Actualizar un PC** (tuyo o del contador)
1. Cerrar la app. **Copia de `datos/`** (sobre todo `datos/soporte.db`: la numeración CTG/NA no se puede rehacer).
2. `git pull` (o copiar los archivos nuevos sin tocar `datos/`) → `pip install -r requirements.txt`.
3. `iniciar.bat`. soporte.db migra solo (`user_version`).

**Health check**: la página abre en :5050; `GET /api/estado` responde (en el contador, `sin_ocr: true`);
la pestaña ③ muestra las mismas semanas que antes de actualizar; desde 1.1.0, ④ Revisión lista los dudosos y abre un recorte; desde 1.2.0, ④ → «Faltan» lista los marcadores; desde 1.3.0, un día con cierre en ③ muestra las filas «según cierre» y débito = crédito.

**Rollback**: cerrar la app → `git checkout vX.Y.Z-anterior` → restaurar la copia de `datos/` hecha en el paso 1
(obligatorio si la versión nueva migró soporte.db: la versión vieja no conoce las migraciones nuevas).
1.2.0 no migra soporte.db, pero escribe marcadores `tipo: "faltante"` en libro.json; la 1.1.0 no los conoce → restaurar la copia de `datos/`.
1.3.0 no migra soporte.db; reescribe los asientos de los días con cierre al recalcular. Volver a 1.2.0: `git checkout v1.2.0` y copiar
`datos/libro.antes-v1.3.0.json` sobre `datos/libro.json` (o la copia de `datos/` del paso 1).

**CI**: no hay. Sugerido (GitHub Actions, Windows): la suite de arriba + gitleaks (historial completo) + `pip-audit`
+ `bandit -r . -x ./datos`. Hoy no están instalados localmente; pre-flight hecho con grep (ver Releases).
**Logs**: Flask no registra cuerpos; cédulas/NIT solo viven en soporte.db y en los Excel.
**Monitoreo RED**: no aplica (un usuario, local). Línea base de calidad: `python medir_precision.py --completo --peores 20 --de-cero` (103 recibos de sept.; informe 20261019-135040: omitidos 5, validados con error 7, dudosos 27; ≈ 4 h, reanudable).
**Repo público**: nada con cifras reales ni datos del negocio (01b/01c, nombre/dirección del local) entra a `main` ni a `origin`.

## Releases
2026-10-19 | v1.3.1 | **Publicada**: M-17 (ajuste R1 como fórmula, helper `consumo_papeles`). Pre-flight OK: suite 18/18, sin claves ni cifras nuevas en v1.3.0..HEAD, sin migración de soporte.db. Rollback a v1.3.0: `git checkout v1.3.0` y volver a exportar el Excel. Falta (usuario): smoke de v1.3.0 + actualizar los PC.
2026-10-19 | v1.3.0 | **Publicada**: tag v1.3.0, push main + tags. Pre-flight OK: suite 18/18, sin claves en v1.2.0..HEAD, debug off, solo 127.0.0.1, sin migración de soporte.db. Cifras reales del ciclo movidas a `01e-cifras-cierre.md` (ignorado) e historial sin publicar reescrito antes del push. Falta (usuario): smoke de 06 y actualizar los PC (runbook).
2026-10-19 | v1.2.0 | **Publicada**: tag v1.2.0, push main + tags (88e61a5..94b7173). Pre-flight OK: suite 18/18, sin claves ni nombre/dirección del local en v1.1.0..HEAD, debug off, solo 127.0.0.1, sin migración de soporte.db. Falta (usuario): actualizar los PC (runbook) y abrir ④ → «Faltan».
2026-10-18 | v1.1.0 | Publicada (ver archive/precision-ocr/07-release.md).
2026-10-17 | v1.0.1 | Publicada (M-1..M-3).
2026-10-17 | v1.0.0 | Publicada.
