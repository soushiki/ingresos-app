# ADR-027 · URL fija por versión = subcarpeta inmutable `/vX.Y.Z/`, publicada desde el PC

Estado: aceptado (2026-10-26, aprobado por el usuario en 3-design del modo contador web)

## Contexto
R6: cada tag tiene una dirección que no cambia. R5: cada versión nueva sigue leyendo crudos v1. Un deploy de Netlify reemplaza el sitio entero, así que las versiones viejas tienen que viajar en cada deploy. 01 dejó dos candidatas.

## Opciones
1. Permalink de deploy (`<id>--sitio.netlify.app`): URL ilegible; retención en plan gratis sin confirmar (01).
2. **Un sitio, una subcarpeta por versión, armada en cada deploy desde lo guardado en git.**
3. Un sitio de Netlify por versión: un proyecto más cada tag, difícil de mantener.

## Decisión
Opción 2. `web/publicadas/vX.Y.Z/` (html, js, css, `nucleo.zip`, `manifiesto.json` con la versión de Pyodide y wheels) se versiona en git y **no se toca nunca más**; `web/publicadas.lock` guarda el sha256 de cada archivo. Pyodide y wheels no van a git: se bajan en el build a `web/cache/` y se verifican contra `web/web.lock`; se sirven compartidos en `/pyodide/<ver>/` y `/py/`. La raíz `/` lista las versiones (la última arriba). Deploy con `netlify deploy` desde el PC del usuario (sin build en Netlify ni acceso al repo); primero borrador, luego `--prod`. Caché `public, max-age=31536000, immutable` en rutas versionadas; la raíz sin caché larga.

## Consecuencias
+ URL legible (`…/v1.10.0/`) que no depende de la retención de Netlify; el sitio se reconstruye desde git + locks si se pierde el PC.
+ Netlify deduplica por hash: subir otra vez Pyodide no cuesta.
− Cada versión suma ~0,5 MB a git. Una versión con un error se reemplaza con un tag nuevo, nunca se edita (la raíz puede marcarla «no usar»).

## Fitness test (`probar_web.py`)
- Todo archivo listado en `publicadas.lock` existe con el mismo sha256 → «ADR-027: la versión publicada vX.Y.Z cambió; publique un tag nuevo».
- `contrato.mjs` corre el crudo v1 de prueba en **cada** carpeta de `web/dist/v*/`; `web_deploy.py` no publica si una falla.
