# ADR-008 · Un recibo que falta es un documento marcador dentro del día

Estado: aceptado (2026-10-18, aprobado por el usuario)

## Contexto
R1 pide anotar desde ④ un número que el nombre de la foto promete y el OCR no leyó, con la foto al lado. Hoy el faltante es solo un
texto en `avisos` del primer recibo de la foto: no tiene id, ni estado, ni foto; ④ no puede listarlo ni cerrarlo.

## Opciones
1. **Lista aparte `dia.faltantes`** en libro.json: limpio, pero el cliente (①) arma y envía el día y habría que llevar la lista por otro camino.
2. **Tabla o archivo aparte**: un segundo almacén que mantener al día con el libro (borrar el día, reemplazarlo, releer).
3. **Documento `tipo:"faltante"` en `dia.documentos`** (`contar:false`, `estado:"falta"|"no_existe"`, `recorte` = foto entera por huella).

## Decisión
Opción 3. Viaja por el camino que ya existe (escanear → ① → «Pasar al libro» → ④). Anotar convierte el mismo id en venta
`origen:"manual"`, `de_foto:<foto>`, `estado:"revisado"`; «no existe» lo deja con motivo como rastro. `faltantes.py` es puro.
Los anotados no entran a la referencia congelada (N3 mide solo el OCR, ADR-007).

## Consecuencias
+ Sin almacén nuevo; borrar o reemplazar un día arrastra sus marcadores. + Todo lo que filtra `tipo=="venta"` los ignora solo.
− Cualquier código que asuma un tipo conocido debe tolerarlo (asientos, exportar, crudo, tabla de ①).
− Releer una foto ya resuelta haría reaparecer el marcador: `reconciliar` lo evita.

## Fitness test (`probar_faltantes.py`)
- `construir_asientos` da el mismo débito, crédito y filas con y sin marcadores. Mensaje: «ADR-008: un faltante movió los asientos».
- `validar.faltantes()` y `referencia.medir` no cuentan un marcador como leído. Mensaje: «ADR-008: un marcador cuenta como recibo leído».
- `faltantes.py` no importa `requests`, `ocr_module`, `flask` ni abre archivos. Mensaje: «ADR-008: faltantes.py dejó de ser puro».
