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
1. Suite verde (17 suites; `probar_imagen.py` es manual): `for f in probar_*.py; do [ $f = probar_imagen.py ] || { printf "$f: "; python $f | tail -1; }; done`
2. `VERSION` + entrada en `CHANGELOG.md`; commit.
3. `git checkout main && git merge --no-ff <rama> && git tag vX.Y.Z && git push origin main --tags`

**Actualizar un PC** (tuyo o del contador)
1. Cerrar la app. **Copia de `datos/`** (sobre todo `datos/soporte.db`: la numeración CTG/NA no se puede rehacer).
2. `git pull` (o copiar los archivos nuevos sin tocar `datos/`) → `pip install -r requirements.txt`.
3. `iniciar.bat`. soporte.db migra solo (`user_version`).

**Health check**: la página abre en :5050; `GET /api/estado` responde (en el contador, `sin_ocr: true`);
la pestaña ③ muestra las mismas semanas que antes de actualizar; desde 1.1.0, ④ Revisión lista los dudosos y abre un recorte.

**Rollback**: cerrar la app → `git checkout vX.Y.Z-anterior` → restaurar la copia de `datos/` hecha en el paso 1
(obligatorio si la versión nueva migró soporte.db: la versión vieja no conoce las migraciones nuevas).

**CI**: no hay. Sugerido (GitHub Actions, Windows): la suite de arriba + gitleaks (historial completo) + `pip-audit`
+ `bandit -r . -x ./datos`. Hoy no están instalados localmente; pre-flight hecho con grep (ver Releases).
**Logs**: Flask no registra cuerpos; cédulas/NIT solo viven en soporte.db y en los Excel.
**Monitoreo RED**: no aplica (un usuario, local). Línea base de calidad: `python medir_precision.py --completo` (107 recibos de sept.).
**Repo público**: nada con cifras reales ni datos del negocio (01b/01c, nombre/dirección del local) entra a `main` ni a `origin`.

## Releases
2026-10-18 | v1.1.0 | **Preparada**: suite 17/17, debug off, solo 127.0.0.1, sin claves (la del spike sale de ~/.claves o .env). 46 commits sin push reescritos (filter-branch; respaldo en `backup/pre-rewrite-v1.1.0`, solo local): sin 01b/01c y sin el nombre del local; 01b/01c en .gitignore; el spike lee NOMBRE_LOCAL/DIRECCION_LOCAL de .env. Ya público desde antes en `ejemplos.py`: dirección y teléfono del POS. Merge/tag/push esperan smoke it. 5 del usuario.
2026-10-17 | v1.0.1 | Publicada (M-1..M-3).
2026-10-17 | v1.0.0 | **Publicada**: smokes it. 1–4 pasan (usuario); suite 8/8, sin secretos ni IDs reales en ba14629..3c7e316 (solo IDs de prueba), debug off, solo 127.0.0.1. main fast-forward a 3c7e316, tag v1.0.0, push a origin. Fuera del repo (público): 01b/01c (cifras reales) y .claude/. Sin cabeceras de seguridad (aceptado: local, Host/Origin revisados). Actualizar los PC: runbook «Actualizar un PC».
