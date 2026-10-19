# 03 · Diseño — M-13 recibos omitidos (aprobado 2026-10-18)

## Summary
- **Un faltante es un documento marcador** (`tipo:"faltante"`) dentro del día, con la foto entera guardada por huella (ADR-006).
  Viaja como cualquier papel: ① lo muestra, «Pasar al libro» lo guarda, ④ lo lista aparte y lo convierte en venta manual o lo cierra
  como «no existe» (ADR-008). Asientos, `faltantes()` y `medir` lo ignoran porque solo miran `tipo=="venta"`.
- **El nombre de la foto** se lee con `leer_nombre()`: un número acortado que cae fuera del rango se corrige por sufijo y **se avisa**
  («3341 → 85341»); un nombre que no se entiende crea un marcador «no entiendo el nombre» en vez de cortar en 1 pieza callado (ADR-009).
- **`medir` guarda por pieza** (tipo, número, 120 caracteres del texto) y da a cada omitido `causa ∈ {tipo, corte, número}`.
- **R5 → ADR-011 (2026-10-19):** reemplaza lo de abajo: número leído a ≤ 1 cifra de un solo faltante, sin OCR nuevo.
- ~~R5 (Should)~~ (ADR-010, reemplazado): solo cuando falta un número, se recorta la cabecera de cada pieza sin número válido, se amplía ×2 y Tesseract busca
  dígitos; si sale exactamente un faltante, se asigna con nota (ADR-010). Sin faltantes, costo cero.
- Sin servicios, tablas ni dependencias nuevas. Todo en `app.py` + `parser_module/contable/` + `static/contable.html`.

## 1 · Qué manda la arquitectura
- Drivers: **R1** (anotar con la foto al lado → la foto entera tiene que existir en el servidor), **R3** (nombre), **R4** (registro por pieza),
  **N2** (+20 % → la lectura extra solo corre cuando hay faltantes), **N3/N4** (la referencia y las pruebas no cambian de vara).
- No mandan: R2 (un `confirm()` en el cliente), R6 (texto del LEEME), N1/N5 (ya se cumplen: todo local, 127.0.0.1). R7/R8 (Could) quedan fuera.

## 2 · Estimación
- 1 usuario, ≈ 20 fotos/día, ≈ 110 recibos/mes; faltantes ≈ 13/mes hoy, ≤ 3/mes con la meta.
- Disco: foto entera reducida a ≤ 1600 px ≈ 300 KB × (fotos con faltante) ≈ 4 MB/mes como mucho. Despreciable.
- Tiempo: R5 ≈ 0,5–1 s de Tesseract por pieza sospechosa; foto típica ≈ 60–90 s → +2 % de media, peor caso (6 piezas) ≈ +8 % < 20 %.
- Presupuesto p99: escanear una foto ≤ 1,2 × M-12; `POST …/anotar` ≤ 300 ms (reescribe libro.json, igual que la revisión de hoy).

## 3 · Componentes (de abajo hacia arriba)
1. **`contable/faltantes.py` (nuevo, puro, sin E/S)** — dueño del marcador: `crear`, `anotar`, `cerrar`, `abiertos`, `reconciliar`.
2. **`contable/validar.py`** — `leer_nombre(nombre) → Nombre(numeros|None, correcciones, entendido)`; `numeros_de_nombre` queda como envoltorio.
3. **`contable/relectura.py`** — `leer_hoja` devuelve `falta` (lista) además de los avisos de hoy; R5 corre aquí, antes de cerrar `falta`.
4. **`contable/referencia.py`** — `medir` arma `piezas` por foto y `causa_de(numero, docs, piezas, esperados)` (pura).
5. **`app.py`** — `_leer_hoja` guarda la foto entera (recortes.guardar) si hay faltante o nombre no entendido y añade los marcadores;
   `_conservar_revisados` pasa por `faltantes.reconciliar`; revisión: `estado=falta` en el listado y dos POST nuevos.
6. **`static/contable.html`** — ① fila de solo lectura con etiqueta «falta»; ④ selector «Faltan» con tarjeta (foto entera + formulario);
   aviso R2 en «Pasar al libro» y en «⬇ Excel»; insignia de ④ con los abiertos.
7. **`LEEME`** — sección «Cómo tomar la foto» (≤ 8 líneas).

## 4 · Datos (todo en `datos/libro.json`, dentro de `dia.documentos`)
- Marcador: `{id, tipo:"faltante", numero:"85388"|"", origen:<nombre foto#pág>, fecha, recorte:<huella foto entera>|null,
  estado:"falta"|"no_existe", motivo:"", contar:false, avisos:["Falta el recibo 85388 en esta foto" | "No entiendo el nombre de la foto …"]}`.
- Anotar = el mismo `id` pasa a `{tipo:"venta", origen:"manual", de_foto:<origen viejo>, estado:"revisado", revisado:true, …campos}`.
- No existe = `estado:"no_existe"`, `motivo` (≤ 200), sigue `contar:false`; queda como rastro.
- Los anotados **no** se agregan a `referencia_<mes>.json` (N3 cuenta solo el OCR; la vara de 107 no cambia, ADR-007).
- Informe de `medir`: `+ piezas:{foto:[{i, tipo, numero, texto}]}`, `+ omitidos_detalle:[{numero, foto, causa}]`, `+ por_causa:{tipo,corte,número}`.

## 5 · Interfaces
- `faltantes.crear(numeros: list[int], origen: str, fecha: str, recorte: str|None, nombre_entendido=True) → list[dict]`
- `faltantes.anotar(doc, campos: dict) → dict` · `faltantes.cerrar(doc, motivo: str) → dict` · `faltantes.abiertos(docs) → list[dict]`
- `faltantes.reconciliar(previos, nuevos) → nuevos sin los marcadores ya resueltos (venta manual con de_foto==origen y mismo número, o no_existe)`
- `validar.leer_nombre(nombre) → Nombre` · `referencia.causa_de(numero, docs, piezas, esperados) → "tipo"|"corte"|"número"`
- `relectura.leer_hoja(...) → {documentos, texto, segundos, avisos, falta}` · R5 usa el `leer_digitos(img) → set[int]|None` que ya existe.
- `GET /api/contable/revision?estado=falta` → marcadores abiertos con `recorte` (foto entera) y `origen`.
- `POST /api/contable/revision/<fecha>/<id>/anotar {campos}` → venta manual; mismas reglas de campos que la revisión (REV_ENTEROS/REV_TEXTOS).
- `POST /api/contable/revision/<fecha>/<id>/no_existe {motivo}` → cierra el marcador.

## 6 · Cuellos de botella y fallos
- Primero se rompe nada por carga; lo frágil es la **relectura de una foto ya revisada**: sin `reconciliar` reaparecerían marcadores
  de números ya anotados. Prueba dedicada (riesgo 2).
- Tesseract ausente o lento → `leer_digitos` da None → R5 se salta (como hoy). Tope de hoja (`factor_tope`) también lo corta.
- No se pudo guardar la foto entera → marcador con `recorte:null`; ④ muestra «sin foto guardada» y el nombre de la foto.
- libro.json se escribe bajo `LOCK` y `_bloqueos` (día con soporte transmitido → 409), igual que la revisión de hoy.

## 7 · Amenazas (ligero: exposed no, 127.0.0.1)
- Frontera navegador↔servidor: `fecha` ISO e `id` `[0-9a-f]{1,32}` por regex; cuerpo ≤ 64 KB; campos solo de la lista blanca;
  `motivo` texto ≤ 200; el id debe ser un marcador `estado:"falta"` (no se puede «anotar» una venta normal). Escritura bajo `LOCK`.
- ④ arma la tarjeta con `textContent`/DOM (regla T11): el nombre de la foto y los avisos son datos leídos. La foto se sirve por
  `/api/contable/recorte/<huella>` (ya valida el nombre). Sin cambios de autenticación: no la hay y la app no sale del equipo (N5).

## 8 · R/N → componente
| Req | Dueño |
|---|---|
| R1 anotar con la foto | faltantes.py (crear/anotar/cerrar) · app.py (foto entera, 2 POST) · ④ tarjeta «Faltan» |
| R2 aviso al exportar | contable.html (`conf` y `xl2`: cuenta `faltantes.abiertos` del día / del rango del libro) |
| R3 nombre acortado | validar.leer_nombre (corrección por sufijo + aviso) · marcador «no entiendo el nombre» |
| R4 causa por pieza | referencia.medir + causa_de · `medir_precision.py` imprime `por_causa` |
| R5 cabecera ampliada | relectura.leer_hoja (solo con faltantes) + leer_digitos |
| R6 consejos | LEEME |
| N2 tiempo | ADR-010 (cero costo sin faltantes) · N3/N4 referencia sin cambios + todas las `probar_*.py` |

## 9 · Riesgos
1. **Código que no espera `tipo:"faltante"`** (asientos, exportar, crudo, ① tabla). Mitigación: fitness test ADR-008 (asientos y Excel
   iguales con y sin marcador) + barrido de `d["tipo"]` en el plan.
2. **Marcadores duplicados al releer una foto ya resuelta.** Mitigación: `reconciliar` con prueba (anotado → no vuelve; no_existe → no vuelve).
3. **R5 asigna un número equivocado** (Tesseract ve el 85391 de otra pieza). Mitigación: solo si sale exactamente un faltante en la
   cabecera recortada, y queda `estado:"dudoso"` con nota → pasa por ④. Si el registro de R4 dice que los 10 son de `tipo`, R5 se replantea
   antes de implementarlo (tarea con compuerta en el plan).
- Sacrificado: no se lee mejor el cuerpo del recibo ni se separan columnas de 3 papeles (R7/R8). A 10× (200 fotos/día) nada cambia: el
  cuello sigue siendo qwen por foto, no esto.
