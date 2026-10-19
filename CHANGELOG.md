# Changelog

## [Sin publicar]

## [1.3.0] — 2026-10-19
Cierre de caja: el día del libro cuadra con el cierre y el pasivo 2815 (domicilios y propinas por pagar) deja de crecer.

### Asientos
- Si el cierre de caja (con total y fecha del día) supera a la venta de los papeles leídos, la diferencia va a la puente 13809501 contra 41401501, con el aviso «Ajuste al cierre (cierre > papeles)». Si los papeles superan al cierre, solo aviso, sin ajuste.
- Cada día con cierre debita 28150502 por las propinas del cierre y 28150501 por los domicilios pagados, contra Efectivo 11050501 («según cierre»). Lo que ya debitaron los vales «pago domicilios» del día se resta: el pago nunca cuenta dos veces.
- Las filas nuevas llevan su fórmula en DATOS OCR (ADR-002); el Excel calcula lo mismo que la app.
- Días sin cierre: sin cambios.

### Datos
- La primera vez que se guarda el libro con esta versión se copia a `datos/libro.antes-v1.3.0.json` (una sola vez, no se pisa). Los días que cambian salen en la hoja «cambió desde que se confirmó» del Excel.

### Conocido
- M-17: el ajuste al cierre es un valor fijo en DATOS OCR; si se corrige una comanda en el Excel, no se recalcula.

## [1.2.0] — 2026-10-19
Recibos omitidos: ningún recibo de una foto se pierde en silencio. Los que el lector no ve quedan como «Falta N» para anotarlos a mano.

### Recibos que faltan
- Si el nombre de la foto dice un número de recibo que no se leyó, queda un marcador «Falta N» con la foto entera (≤ 1600 px). El marcador no cuenta en asientos, Excel ni DATOS OCR (ADR-008).
- Pestaña ④ **Revisión** → selector «Faltan»: **Anotar** (formulario manual con el número puesto; recalcula el día) o **No existe** (motivo obligatorio). La insignia de ④ suma dudosos y faltantes; la fila «falta» aparece en ①.
- Aviso (no bloquea) «quedan N recibos sin anotar» al «Pasar al libro» (cuenta también el día en pantalla) y al «⬇ Excel».

### Lectura
- Nombre de la foto acortado: «85334-3341-…» se entiende como 85341, con el aviso «3341 → 85341» (ADR-009). Si el nombre no se entiende, queda un marcador «No entiendo». Los nombres del escáner (`comandas2026…`) y las fotos `IMG_` no generan marcador.
- R5 por cercanía (ADR-011): si el número leído está a 1 cifra del único que falta, se le asigna y el recibo queda «dudoso» para que pase por ④.

### Medición
- `medir_precision.py` registra la causa de cada omitido (corte / número / tipo), imprime una línea por foto y guarda el avance: si la corrida se corta, sigue donde iba (`--de-cero` empieza de nuevo).
- Sobre 103 recibos de septiembre, los omitidos bajan de 13 a 5 (4,9 %). Los validados con error se quedan en 7. La meta N3 (≤ 2) no se alcanza; se aceptó en ADR-011.

### Arreglado
- Una venta anotada a mano no se duplica cuando se relee la foto. El marcador «No entiendo» no se duplica al releer.

### Documentación
- LEEME §7 «Cómo tomar la foto»: fondo oscuro y liso, una columna, cerca y sin cortar el pie del recibo.

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
