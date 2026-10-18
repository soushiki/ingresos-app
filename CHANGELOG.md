# Changelog

## [Sin publicar]

## [1.1.0] — 2026-10-18
Precisión del OCR: cada recibo se valida, se relee con variantes si falla y lo dudoso pasa a revisión con su foto.

### Lectura de recibos
- Validación por recibo (`validar.py`): campos obligatorios y sumas (subtotal, pagado − cambio, total), número de la foto contra el nombre del archivo (R5), precio contra la carta (R6) y segundo lector de dígitos con Tesseract (R3: no ver = nota suave; otro número = dudoso).
- Relectura (`relectura.py`): si V0 no valida, hasta 3 pasadas con variantes (V4 Real-ESRGAN opcional, V3, V1, V2), voto por campo y foto borrosa (Laplaciano) exige dos lecturas iguales; tope de tiempo.
- Hoja con varios recibos: `separar` usa la cantidad esperada del nombre del archivo (35/43 fotos bien cortadas, antes 1/43).
- Catálogo de precios (`datos/catalogo.json`, auto desde el libro + manual que gana), rehecho en cada arranque y tras confirmar.

### Revisión
- Estado por recibo: validado / dudoso / revisado (los datos viejos migran al leer). Releer nunca pisa un «revisado».
- Pestaña ④ **Revisión**: recorte de la foto, motivo, pasadas, candidatos clicables, confirmar o editar (recalcula el día); selector Dudosos/Revisados.
- DATOS OCR suma columnas Recibo y Motivo; dudoso en naranja, otros avisos en amarillo.
- Recortes por huella (`GET /api/contable/recorte/<nombre>`) y borrado de huérfanos.

### Medición
- `medir_precision.py` contra una referencia congelada (`--completo`, `--variantes`, `--peores`, `--exportar` para entrenamiento futuro).
- Sobre 107 recibos de septiembre: con error 12,2 % → 3,4 %; las metas N3 de omitidos y dudosos aún no se cumplen (ver 08-maintenance).

### Arreglado
- Una comanda cuyo número queda a más de `salto_comanda` (30, configurable en contable.json) de las demás comandas del día genera un aviso (M-4).
- «Falta la mesa» no aplica a domicilios; la fecha no se edita en Revisión; un recibo sin número no se duplica al editarlo; páginas de un PDF largo se leen como en la app.

## [1.0.1] — 2026-10-17
Arreglos menores del import de datos crudos y del chequeo de Host.

### Arreglado
- Importar datos crudos rechaza un papel con `valor` negativo (solo el cierre lleva negativos: faltante) (M-1).
- Importar datos crudos rechaza un día con dos papeles de igual `id` (M-2).
- Un Host con «@» (user@host) se rechaza con 403 aunque cambie la versión de Werkzeug (M-3).

## [1.0.0] — 2026-10-17
Primera versión con número. Documento soporte (Res. DIAN 167/2021) y app partida en dos PC.

### Libro contable (fase A)
- Hoja **DATOS OCR** (una fila por papel leído, con origen, estado y aviso) como primera hoja del Excel;
  **MOVIMIENTOS** se calcula desde ella con fórmulas (SUMIFS), así una corrección a mano se refleja.
- Cuentas puente para venta sin medio y gasto sin cuenta; hoja **AVISOS** (filas sin código, días que
  cambiaron desde que se confirmaron, efectivo 0 con propina/domicilio).
- Tope de propina + domicilio al efectivo; días con solo pendientes se guardan.

### Documento soporte (fase B)
- Proveedores no obligados a facturar (tipo/número/DV validados) y alias por tercero.
- Compras agrupadas por proveedor y semana (lun–dom) con fecha límite y estado (en plazo / vence pronto / vencida).
- Numeración reservada CTG 1–10000 en SQLite (`datos/soporte.db`), todo o nada; Excel con RESUMEN y una hoja por documento.
- Compra manual, transmitido (CUDS), anular con motivo, nota de ajuste (NA, contador aparte); días con documentos bloqueados.
- Pestaña ③ «Documento soporte».

### Dos PC (OCR separado)
- Exportar/importar **datos crudos (.json)** versionado con sha256 (ADR-004); informe nuevos/iguales/conflictos/bloqueados.
- `SIN_OCR=1`: la app arranca sin Ollama y ① ofrece «Importar datos». Guía `LEEME-contador.md`.

### Seguridad
- Host y Origin locales exigidos en toda la app (CSRF, DNS rebinding).
- Texto que empieza por `= + - @` se escribe como texto en los Excel (sin inyección de fórmulas).
- Topes de importación (|valor| ≤ 10^10, texto ≤ 20.000, ≤ 2.000 documentos por día, JSON anidado → 400).

### Arreglos
- Fechas OCR con año mal leído: si caen a más de 7 días del día, se usa la del día y se avisa.
- «Sin Texto» ya no aparece como proveedor; compras nuevas en una semana ya documentada se numeran aparte.
- Sin scroll lateral a 375 px en ①, ② y ③.
