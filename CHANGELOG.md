# Changelog

## [Sin publicar]

## [1.9.0] — 2026-10-26
Recuperar número con Indra (M-26): cuando qwen no da el número de un recibo Ascomp, la app lo toma de los números que Indra leyó en el recorte.

### Lectura
- `leer_recibo` guarda en `lectura.digitos` la unión ordenada de los números que vio el segundo lector (Indra) en las variantes del recorte.
- Paso 4 de `leer_hoja`: si qwen no da candidato para un faltante, se prueban los números de `lectura.digitos`. Se asigna solo si hay un candidato único dentro del rango que da el nombre de la foto y no es el número de otra venta de la misma foto. qwen siempre gana.
- La venta recuperada va a ④ como «dudosa» con el motivo «Número recuperado por el segundo lector (Indra leyó …)».

### Medición
- El informe de `medir_precision.py` suma `recuperados` y `recuperados_con_error`.
- Referencia de 103 recibos de sept. (informe 20261026-000348 frente a 20261020-225729): omitidos 5 → 0, recuperados 4 con el número correcto, validados con error 7 → 7, dudosos 26 → 27.

## [1.8.0] — 2026-10-25
Cuenta PUC por origen e ítem (M-27): cada papel recibe su cuenta por lo que es (comanda, cierre, gasto, extracto) y por lo que trae cada ítem. Una factura con ítems de varias cuentas se reparte. Lo que no se puede decidir va a la cuenta puente y a ④ Revisión.

### Clasificación
- Motor por capas (`clasificar.py`): origen → enseñado → frases/léxico → minado del manual y proveedor → vecino parecido → puente. Cada ítem trae su capa y su motivo. Venta, Rappi y cierre van a 41401501 («origen: comanda»).
- `herramientas/minar_manual.py` aprende del Excel manual (jun–oct) y deja `modelo_manual.json`: palabras, bigramas, proveedores y vecinos, con la fila de donde salió cada uno. No guarda valores ni fechas. Los terceros que son personas van a `terceros_cuentas.json`, que es local y no se versiona: los de nómina, capital, socios y anticipos, y cualquier tercero con un nombre de pila y sin marca de empresa.
- `por_confirmar.json`: alias de cuentas, las 8 decisiones del contador marcadas «por confirmar» y los umbrales. Al final del motor, `puc_valida` revisa cada código contra el PUC. La decisión 4 ya está contestada: el recibo de agua del acueducto va a 51352501 y el «agua» que se compra va a 14050502.
- Medido con jun–ago contra sept–oct: 67,2 % de acierto por ítem y 87,3 % de precisión en lo que el motor decide (N1, ADR-025).

### Papeles y DATOS OCR
- `items_de(doc)`: si los ítems de una factura cuadran con el total (±1 %), se usan los ítems; si no, va un solo ítem con el detalle y el proveedor. Los papeles viejos conservan su cuenta a mano.
- DATOS OCR pone una fila por (papel, cuenta). Una diferencia de más del 1 % entre los ítems y el total va a la puente, y queda en revisión. Una diferencia de 1 % o menos se suma al ítem mayor. Cada papel da N débitos y 1 crédito.
- Si la cuenta se puso a mano, se respeta. Los ítems que están en la puente se reclasifican en cada pasada.

### Interfaz
- Tarjeta del papel: «Cuenta por ítem». Al cambiar la cuenta de un ítem, ese ítem queda manual y se aprende para el siguiente igual. El proveedor solo se aprende si todos sus ítems van a la misma cuenta.
- Botón «Reclasificar mes» (`POST /api/contable/reclasificar`): primero muestra la vista previa (antes → después, y los días cuyo débito o ingresos cambian). Aplicar solo funciona si la huella no cambió (si cambió, responde 409). Se hace en 1 escritura, no toca lo manual y queda un rastro `reclasificaciones[]` por día.
- `docs/por-confirmar-contador.pdf` (lo genera `por_confirmar_pdf.py`): las 8 decisiones y los 5 alias, con las filas del manual y los ítems del libro que afecta cada punto.

### Excel
- Cada mes trae ahora la hoja «BALANCE x CTA <MES>» antes de su «MOVIMIENTOS», con la forma del Excel manual: todas las cuentas del plan, saldo inicial, débito, crédito y saldo final, y el resumen por clase. Son fórmulas sobre MOVIMIENTOS (por la celda de cada fila, no por la columna entera). El saldo inicial sale del mes anterior si está en el mismo archivo; el primer mes va en 0, con una nota. Una fila de control muestra la diferencia con MOVIMIENTOS, que debe dar 0.
- Los códigos de cuenta se revisan contra el PUC (puc.com.co; copia local en `parser_module/contable/puc_cuentas.json`). Una cuenta o subcuenta que no existe sale en AVISOS. Los nombres del PUC se usan cuando un código no está en el plan.

### Extracto
- El extracto se lee de todas las hojas del archivo que tengan Fecha, Descripción, Referencia y Valor, y no solo de «Hoja 1»: la hoja «MOVIMIENTOS» trae el mes completo y la «Hoja 1» de septiembre llega solo al 23. Una línea que está en las dos hojas entra una sola vez, con la clave de «Hoja 1», así que un extracto importado antes sigue reconocido («ya estaban»).

### Datos
- Sin migración de soporte.db. VERSION_RESPALDO sigue en 1.6.0. «Reclasificar mes» hace su propio respaldo único, `datos/libro.antes-v1.8.0.json`, la primera vez que aplica.
- Archivos nuevos en git: `modelo_manual.json`, `por_confirmar.json`, `terceros_cuentas.example.json`. Archivo local: `terceros_cuentas.json`; si falta, se usa el `.example`.

## [1.7.0] — 2026-10-24
Indra OCR: un lector local nuevo lee los números de los recibos y endereza las fotos torcidas o de lado. Si Indra no está, todo funciona con Tesseract como en 1.6.0, y la pantalla lo avisa.

### Lectura
- El segundo lector de R3 (los dígitos de cada recorte) es Indra (indra-ocr 1.1.2) en vez de Tesseract-dígitos. Con los 103 recibos de sept. hay 5 omitidos (igual que antes), 26 dudosos (antes 27) y 7 validados con error (igual). No hay totales peores.
- Enderezado: antes de recortar se detectan el giro (0/90/180/270) y la inclinación de cada hoja, y se corrigen con fondo blanco. Una hoja derecha (giro 0 y menos de 0,3°) no se toca, así que salen los mismos recortes que en 1.6.0. Probado con 20 hojas en 7 ángulos: 18 derechas y 2 de lado, inclinación ≤ 0,9°, ≤ 0,37 s por hoja.

### Trabajador y respaldo
- Indra corre en su propio proceso (`indra_venv`, Python 3.14). Arranca con la primera foto y se cierra solo, en ≤ 5 s, cuando se cierra o se mata la app. Si se cuelga o muere, se reinicia una vez; si falla de nuevo, se usa Tesseract el resto de la sesión.
- Si no hay `indra_venv` o Indra se cae, se usa Tesseract y aparece la banda «Indra no disponible: se usa Tesseract» en la pantalla contable. `/api/contable/capacidades` trae `motor` y `aviso`.

### Instalar
- `instalar_indra.bat` comprueba que esté Python 3.14, crea `indra_venv\`, instala `indra_requisitos.txt` y baja los modelos una vez (luego funciona sin internet). Se puede correr otra vez sin problema. `probar_indra.py` revisa la versión y que las lecturas se repitan.
- Licencia de los pesos (OpenRAIL-M modificada, de Datalab): ver README «Indra» y `docs/licencias/`.

### Datos
- Sin migración de soporte.db y sin recálculo del libro (VERSION_RESPALDO sigue en 1.6.0). Solo cambia cómo se leen las fotos nuevas o re-subidas.

## [1.6.0] — 2026-10-20
Extracto bancario: el Excel que se descarga del banco entra al libro, cada línea clasificada y con su asiento; lo dudoso queda para que elijas la cuenta.

### Importar (pestaña ⑤ «Extracto»)
- Subir el .xlsx del banco (hoja «Hoja 1», 4 columnas; tope 5 MB y 5 000 filas). Todo o nada: un archivo malo no cambia el libro y muestra el motivo.
- Re-subir el mismo archivo o uno que se cruza no duplica: cada línea tiene una clave y se mezcla por ella. Resumen «N nuevas, M ya estaban · K por revisar».
- «Importaciones» lista cada archivo subido y «Deshacer» lo quita y recalcula los días; borra los días que el archivo había creado y quedaron vacíos.

### Clasificar
- Reglas en `extracto_reglas.json` (prefijo + signo → concepto → destino): GMF 4x1000 → 53152001, rendimientos → 42100505, Rappi → 13452501, abonos de tarjetas, QR, llave y Rappi → su casilla del día. Las cuentas quedan «por confirmar» con el contador.
- Lo que no encaja sale «por revisar» contra la cuenta puente 51959501, con un pendiente en el día.
- Memoria por tercero: al asignar una cuenta con «recordar», las próximas transferencias a ese tercero salen solas («recordada»). Las descripciones sin tercero nunca se recuerdan.
- Una salida igual a una factura pagada por banco (±3 días) se enlaza a ella y no da asiento propio; se confirma o se rechaza. Con 2 o más candidatas queda «¿cuál factura?». Una factura se enlaza a una sola línea.

### Asientos y casillas
- Casilla del banco vacía → se llena con el extracto. Digitada → manda la digitada y el día avisa la diferencia; «Usar extracto» la borra.
- «Totales del mes» por concepto, con la diferencia digitado vs extracto por medio.
- Editar o recalcular un día conserva su extracto. El Excel exportado trae las filas «Extracto».

### Datos
- Sin migración de soporte.db. Importar recalcula los días tocados: los guardados antes de v1.3.0 toman las reglas de cierre (filas 13809501 y 2815xx que hoy faltan). La primera vez que se guarda con esta versión se copia a `datos/libro.antes-v1.6.0.json`.

## [1.5.0] — 2026-10-20
Medio de pago: el libro y el Excel usan un solo vocabulario de 8 medios (Efectivo, Transferencia, Bre-B, QR, PSE, Tarjeta, Crédito personal, App).

### Lectura
- Un solo mapa (`medio_canonico`, en `normalizacion.json`): Nequi/Daviplata/transferencia/consignación → Transferencia; Datáfono/Visa/débito/crédito con tarjeta → Tarjeta; Rappi → App; llave → Bre-B. Un medio desconocido o «(sin medio)» queda vacío con aviso, nunca inventado.
- El texto del papel se guarda aparte (`medio_detalle`): las descripciones de recaudo siguen diciendo «Nequi»/«Daviplata».

### Asientos
- Las filas que no son de caja (2815 propinas/domicilios, puentes 13809501/51959501, «Total vendido» del cierre, ajustes) quedan con medio vacío, como el manual.
- Venta mixta sigue repartida por medio; ninguna fila dice «Mixto». Factura de gasto «Mixto» → medio del mayor pago, con aviso «revisa el medio».
- Los recaudos de banco/Rappi conservan «· Ordenes: …» en la descripción.

### App y Excel
- Las listas de medio de la app (factura manual, ④ Revisión) muestran los 8; una factura con «Nequi» se guarda como Transferencia.
- DATOS OCR trae la columna nueva «Medio según el papel» (al final).

### Datos
- Sin migración: el libro viejo sale con los 8 medios al recalcular. La primera vez que se guarda con esta versión se copia a `datos/libro.antes-v1.5.0.json`.

## [1.4.0] — 2026-10-19
Rappi: cada papel de Rappi entra al libro como venta por cobrar a Rappi, con su ID y su valor.

### Lectura
- Nuevo tipo de papel «rappi» (texto con «Rappi» y «Total sugerido a facturar», o «ID» largo junto a «Plataforma»/«Fecha orden»). En una foto de comandas no se fuerza a venta del POS.
- Número del documento = ID de Rappi; valor = «Total sugerido a facturar» (si falta: «Subtotal» con aviso; si tampoco: 0 + aviso «No se leyó el total de Rappi», nunca inventado). Medio «Rappi», tercero Rappi. La fecha sigue la regla de la carpeta.
- Al subir la foto, el papel conserva ID y valor (no se re-lee como comanda) y `validar` solo pide ID y valor (sin hora, mesa ni aritmética).

### Asientos
- Venta Rappi → débito 13452501 (por cobrar a Rappi, medio App) / crédito ingresos; el abono semanal del bloque «rappi» del extracto la salda (sin cambios).
- El ID de Rappi no entra a la numeración de comandas (sin faltantes ni avisos de secuencia falsos). El mismo ID dos veces = una sola venta, la segunda con «duplicado de».

### Datos
- La primera vez que se guarda el libro con esta versión se copia a `datos/libro.antes-v1.4.0.json` (una sola vez, no se pisa; la versión del respaldo es la constante `VERSION_RESPALDO` de `app.py`).
- Los papeles de Rappi ya guardados no cambian al recalcular: hay que volver a subir sus fotos (ver runbook).

## [1.3.1] — 2026-10-19
Arreglo M-17: el ajuste al cierre se recalcula en el Excel.

### Asientos
- DATOS OCR guarda el total del cierre, y el ajuste «cierre > papeles» es una fórmula (total − MIN(total, papeles)): si se corrige una comanda en el Excel, el ajuste cambia con ella.
- La venta de los papeles sale de un solo helper (`consumo_papeles`), el mismo para la app y el Excel. Una cortesía ya no cuenta como papel, así que el ajuste no queda corto.
- Rige al recalcular el día; sin migración de datos.

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
