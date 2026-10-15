# 📒 Libro contable (pantalla principal) · `python app.py`
Genera las filas de tu «Reporte contable» (débito y crédito) a partir de los papeles del día y las pasa a una tabla con las
mismas columnas: **Fecha · Código · Nombre cuenta · Tercero · Descripción · Débito · Crédito · Reporta · Medio de pago**.
La versión anterior (columnas de ganancias y pérdidas por día) sigue en http://127.0.0.1:5050/simple.

**Fotos y PDF, por día y por grupo.** Cada día tiene tres grupos: **📋 cierre** (el «Cierre de caja resumido» del POS),
**🧾 comandas** (los recibos de venta) y **💸 gastos** (gastos de caja, recibos de caja menor, facturas). Puedes soltar los archivos
en la zona de cada grupo, o en «Automático» para que la app detecte el tipo de cada papel. Acepta fotos y **PDF** (instala `pip install pymupdf`):
- PDF con texto digital → se lee su texto (instantáneo y exacto, sin OCR).
- PDF escaneado → cada página se convierte en imagen y la lee el modelo. Si un PDF con texto sale mal, marca «PDF como imagen».
- Cada página cuenta como un papel aparte y se ve cuántas lleva cada grupo. Un PDF o foto con papeles de varios días se reparte
  solo en un «día» por fecha (pestañas arriba). Si el tipo detectado no es el que querías, cámbialo en la fila: el papel se vuelve a leer.
- **Cruce cierre ↔ papeles:** lo que dice el cierre del POS (venta en efectivo, tarjetas, propinas, gastos) se compara con la suma de
  tus comandas y gastos. Una diferencia significa que falta un papel o se leyó mal. Puedes corregir las cifras del cierre a mano.

**Carpeta del día (como la organizas tú).** Usa **📁 Subir carpeta del día** con una carpeta así: `15 SEPT 26/` con las subcarpetas
`CIERRE/`, `COMANDAS/` y `GASTOS/`. La app toma el **grupo** de la subcarpeta (o del prefijo del archivo: `comandas2026…`) y el **día**
del nombre de la carpeta (`15 SEPT 26`, `2026-09-15`, `15-09-26`); si el papel trae otra fecha escrita, se va a ese día.
Para hojas escaneadas la app, antes de leer:
- **Gira** las hojas de lado o al revés (detección automática con Tesseract; sin Tesseract se desactiva y usas el botón ↻ de cada archivo).
- **Recorta** el blanco de los márgenes y, en las comandas, **separa cada recibo** de la hoja (3 o 4 por página) y lee uno por uno.
- El botón **↻** junto a cada archivo lo gira 90° y lo vuelve a leer si salió mal. **⤴** une un papel de gastos con el de arriba
  (una factura que salió en dos hojas).
**Cierre ↔ comandas ↔ gastos.** El cierre trae el rango de recibos (Factura inicial/final), el número de transacciones y las cifras
por medio de pago; la app los compara con tus comandas y avisa **qué recibo falta** (en tu 15/09: el 85610, $24.900 en efectivo).
Cada comanda se reparte entre efectivo y banco: lo electrónico cubre primero el consumo, luego el domicilio y por último la propina;
solo lo que entró en **efectivo** va al bloque de efectivo (propinas y domicilios incluidos). Para Tesseract, instala el programa
(Windows: `winget install UB-Mannheim.TesseractOCR`) y `pip install pytesseract`.

**① Papeles del día**
1. Elige el día y sube las fotos: recibos de venta, gastos de caja, recibos de caja menor, facturas de proveedores. Una foto
   puede traer **varios papeles**: se separan solos. Cada papel es una fila que puedes corregir.
2. El recibo de caja menor manuscrito y el gasto de caja impreso son el mismo gasto: se detecta y se **cuenta una sola vez**
   (se ve tachado; el visto «Contar» lo puedes cambiar).
3. Cada gasto recibe una **cuenta**: la que tú enseñaste, la del proveedor según tu historial, o por palabras
   («transportes» → 51355001, «pago a domicilio» → 28150501, «papel» → 51953001). Si es dudosa sale en **amarillo**; al elegirla
   tú, la app lo aprende.
4. Los recaudos del banco (Bre-B/LLAVE, tarjetas, QR) los escribes de tu extracto: no salen de los papeles.
5. Abajo ves los **asientos del día**, igual que en tu Excel, y si **débito = crédito**. Los avisos te dicen qué falta.
6. **Confirmar y pasar al libro**: pregunta antes si el día no cuadra o si quedan cuentas sin confirmar.

**② Libro contable**: los días confirmados con sus asientos, filtro por fechas, ganancia/pérdida del rango y **Excel**
(una hoja «MOVIMIENTOS <MES>» por mes con tus columnas, colores y totales con fórmulas, más una hoja «RESULTADO»).
Con **✎ Reabrir** corriges un día y lo vuelves a confirmar.

**Reglas de contabilidad que aplica** (de tu libro): el efectivo de un recibo = consumo en efectivo + propina + domicilio
(la tarjeta cubre primero el consumo); las ventas en efectivo → débito Efectivo, créditos Propinas, Domicilios y Restaurante;
los gastos de caja menor se agrupan por cuenta («Recibos: 210 al 213»); las facturas pagadas por banco → débito al gasto,
crédito a Bancolombia. Configuración opcional en `datos/contable.json`: `negocio`, `nit`, `cuenta_recaudo`,
`reporta_efectivo`, `reporta_banco`.

**Ojo con el resultado**: los insumos (cocina, barra, empaques) quedan como activo; la ganancia real necesita el inventario final del mes.

Pruebas: `python probar_contable.py` (tus papeles de ejemplo) · `python probar_dia15.py` (los números reales de tu 15/09, sin datos personales) · `python probar_pdf.py` · el plan de cuentas y el historial de proveedores salieron de tu Excel
(`parser_module/contable/*.json`).

# 📒 Ingresos Diarios

Fotos de cierres de caja manuscritos → tabla editable → Excel. Todo corre en tu computador (nada sale a internet).

## Instalar (una sola vez)
```bash
pip install -r requirements.txt
ollama pull qwen2.5vl:7b        # o qwen3-vl:8b; compara cuál lee mejor tu letra
```

## Cómo se trabaja: dos módulos
**① Análisis del día** (borrador, nada se guarda todavía)
1. Arrastra las fotos de las facturas del día. Cada imagen se lee y cae en el día que dice su fecha; una imagen sin fecha
   (por ejemplo, la segunda mitad de una factura larga) se queda en el día en el que la subiste. Si subes fotos de varios días
   a la vez, se separan solas en un «día» por fecha.
2. Cada factura aparece como una fila que puedes corregir. Abajo está el **Resultado del día**: una sola cifra por columna,
   las columnas calculadas (ventas del día, ganancia/pérdida) y los controles que avisan si algo no cuadra.
3. Cómo se combinan las facturas del mismo día (selector «Cifra repetida en varias facturas»):
   - *Contarla una vez* (por defecto): si la misma cifra sale en dos imágenes se cuenta una sola vez (típico de una factura
     larga fotografiada con solapamiento); cifras distintas se suman (facturas distintas).
   - *Sumarlas*: todas las facturas se suman, aunque se repita una cifra.
   Las cifras combinadas quedan en amarillo con el motivo (pasa el cursor). Puedes escribir encima de cualquier cifra del
   resultado (doble clic para volver al cálculo).
4. Cuando todo cuadre: **✔ Confirmar y pasar a la tabla**. Si quedan cosas por revisar, te lo recuerda antes de confirmar.

**Fechas**: se escriben como `dd/mm/aaaa` (también `11-08-26` o `11082026`); la barra diagonal se pone sola.
La fecha se confirma al salir del campo o con Enter, nunca mientras escribes. Si a una factura le pones una fecha distinta a
la del día, te pregunta si quieres moverla; una fecha imposible (31/02) se marca en rojo y no cambia nada. El botón 📅 abre el calendario.

**② Tabla de días**: solo contiene días confirmados, con el total de cada columna y las facturas que lo componen.
Filtra por fechas, mira ganancias/pérdidas y el neto, descarga el Excel, o **✎ Reabrir** un día para agregarle otra factura
o corregirlo (queda como borrador hasta que lo confirmes de nuevo).

**Excel**: hoja *Ingresos* (un día por fila, totales con fórmulas), *Resumen mensual* y *Detalle por factura*
(lo leído en cada imagen; el día cuenta una vez las cifras repetidas, el detalle las muestra tal cual salieron).

## Plantilla por defecto: «Restaurante · ganancias y pérdidas» (mínima)
Los cierres de caja no comparten los mismos campos, así que la app ignora casi todo y se queda con lo necesario para
saber si el día fue ganancia o pérdida (10 columnas):
- **Se leen del recibo (8):** venta en efectivo, venta con tarjetas, venta por transferencias/app, ventas totales (impresas),
  gastos/egresos, pago a domiciliarios, faltante/sobrante de caja y ganancia/pérdida (impresa).
- **Se calculan (2, columnas ƒ):**
  - *Ventas del día* = ventas impresas; si el recibo no las trae, la suma de efectivo + tarjetas + transferencias.
  - *Ganancia / pérdida del día* = lo que el recibo diga («Utilidad», «Pérdida»…); si no dice nada,
    ventas − gastos − domiciliarios ± faltante/sobrante.
- Es un resultado **de caja**, no contable: el recibo no trae costo de los alimentos ni nómina. Para descontarlos, edita la
  fórmula en ⚙ Columnas (p. ej. `… - [Ventas del día] * 0.32` para un costo de alimentos del 32 %).
- La plantilla anterior (recibo POS de referencia, con efectivo esperado/contado y controles) sigue en ⚙ Columnas → Plantillas.

## Sinónimos de ganancia y pérdida (léxico con signo)
`parser_module/lexico.py` trae los términos que usan los cierres de caja y el signo que implica cada uno:
- **Pérdida (−):** pérdida, déficit, quebranto, faltante, falta…  **Ganancia (+):** ganancia, utilidad, beneficio, sobrante,
  excedente, sobra…  **Tal como viene:** resultado, balance, diferencia, descuadre, «ganancia/pérdida», «faltante/sobrante».
- Por eso «FALTANTE 138.950» se guarda como −138.950 aunque el recibo no traiga el signo menos.
- Si el término no dice el signo («Descuadre 5.000»), la celda queda en amarillo para que decidas.
- Sinónimos con **+** delante (p. ej. `+crédito`, `+débito`) son *partes*: se suman si el recibo no trae el total.
- Se detectan también con errores de lectura («Faltanre», «Perdidas»), con la etiqueta antes o después del valor, o en otra línea.
- Prueba: `python probar_restaurante.py` (21 cierres escritos de formas distintas).

## Recibo POS «Cierre de caja resumido» (plantilla de referencia)
Esta plantilla se hizo a partir de la foto de referencia
(`parser_module/ejemplos_pos/recibo_referencia.jpg`). Se carga desde **⚙ Columnas → Plantillas**.
- **Columnas base** (17): base de caja, venta en efectivo, tarjetas (sin y con propina), transferencias/app, propinas
  (efectivo, tarjeta, app, total), domicilios (vendidos, número, pagados), otros ingresos, gastos, efectivo esperado en caja,
  efectivo contado por el cajero y el faltante/sobrante impreso (con signo negativo).
- **Ganancia / Pérdida de caja** (columna calculada ƒ) = efectivo contado − efectivo esperado. Negativo = pérdida (faltante),
  positivo = ganancia (sobrante). La parte superior de la tabla resume ganancias, pérdidas y neto del día.
- **Controles**: avisan cuando algo no cuadra (por ejemplo, el faltante impreso ≠ contado − esperado, o las propinas no suman).
  Sirven para detectar dígitos mal leídos en fotos pequeñas o borrosas.
- Los renglones del recibo que no son columnas (ventas por hora, por mesero, denominaciones…) se ignoran.
- Las fotos largas y angostas se parten en trozos ampliados antes de leerlas, para que el modelo distinga los dígitos.
- Las fórmulas se escriben con `[Nombre de la columna]` y se pueden editar en ⚙ Columnas (tipo «Cálculo»). En el Excel
  son fórmulas vivas, y el resumen mensual separa ganancias y pérdidas.

## Define tus columnas (antes de escanear)
Botón **⚙ Columnas**: eliges cuántas columnas quieres, cómo se llaman, su tipo (Monto $ o Cantidad) y, si hace falta,
sinónimos (cómo las anotan en la planilla). Puedes reordenarlas, pegar una lista (una por línea) o volver a las 12 originales.
- Las columnas se guardan en `datos/esquema.json` y se usan en la tabla, el parser y el Excel.
- Si las cambias **después** de escanear, lo ya leído se reinterpreta al instante sin repetir el OCR, y lo que editaste a mano se conserva.
- Si el nombre coincide con uno de los originales («Efectivo», «Domicilio»…) hereda su vocabulario (Efec, Domi…).
- El historial guarda cada día con las columnas que existían; el Excel del historial usa las columnas actuales.

## Cómo se usa: dos módulos
**① Análisis del día** (donde se lee, se calcula y se verifica)
1. Abre Ollama (ícono de la llama junto al reloj) y haz doble clic en `iniciar.bat` (o `python app.py`). Se abre http://127.0.0.1:5050.
2. Arrastra las **facturas del día**: una o varias imágenes. Cada una se lee y aparece como una fila.
   - Las que traen la **misma fecha** se agrupan en un solo día. Una imagen de otra fecha crea otro día (pestañitas arriba).
   - Una imagen **sin fecha** (típico de la segunda parte de una factura larga) se queda en el día que estás viendo.
3. Abajo está el **Resultado del día**: las cifras de todas las facturas combinadas, las columnas calculadas
   (ventas del día, ganancia/pérdida), los controles y las dudas.
   - Si la misma cifra sale en dos imágenes (una factura larga fotografiada con solapamiento) se cuenta **una sola vez**;
     si son distintas se **suman**. En ambos casos queda en amarillo para que lo verifiques. Hay un selector para «sumarlas siempre».
   - Puedes corregir cualquier cifra del día a mano (borde azul; doble clic vuelve al cálculo) o marcar todo como revisado.
4. Cuando todo cuadre: **✔ Confirmar y pasar a la tabla**. Pide fecha, que no haya facturas pendientes o con error, y
   avisa si quedan dudas o controles que no cuadran.

**② Tabla de días** (solo días ya verificados)
- Una fila por día con sus totales, la ganancia/pérdida, cuántas facturas lo componen y las notas. Resumen de ganancias, pérdidas y neto.
- **✎ Reabrir** devuelve un día al módulo ① con todas sus facturas para corregirlo; al confirmarlo reemplaza el guardado.
- Filtro por fechas y **⬇ Excel**: hojas *Ingresos* (totales con fórmulas), *Resumen mensual* y *Detalle por factura* (de qué imágenes salió cada día).

Si una etiqueta no se reconoce (p. ej. «gas»), el panel de la derecha deja elegir su columna con *Enseñar*; no vuelve a preguntar.
Al cerrar la página se pierden los días que sigan sin confirmar (el navegador avisa).

## Dónde queda todo
Carpeta `datos/`: `historial.json` (días confirmados, con sus facturas) y `alias_negocio.json` (etiquetas que has enseñado). Haz copia de esa carpeta de vez en cuando.

## Estructura
`ocr_module/` (imagen → texto) · `parser_module/` (texto → tus columnas) · `excel_export.py` · `app.py` + `static/index.html`.
Pruebas sueltas: `probar_imagen.py` (una foto), `probar_parser.py` (ejemplos del parser) y `probar_esquema.py` (columnas personalizadas).

## Si algo falla
- «Ollama sin conexión»: abre la aplicación Ollama o ejecuta `ollama serve`.
- Error de modelo no instalado: `ollama pull <modelo>` y elígelo en la lista de arriba.
- Cambiar el puerto: variable `PORT=5051` en `.env`.

## Carpeta del día (📁 Subir carpeta)
Elige la carpeta de un día con subcarpetas **CIERRE**, **COMANDAS** y **GASTOS** (o archivos que empiecen por esos nombres): cada archivo toma su grupo del nombre, los PDF con texto se leen sin OCR y los escaneados/fotos se giran, recortan y separan por papel. El cierre del POS se cruza con tus comandas y vales (rango de facturas, tarjetas, transferencias, propinas, domicilios, descuentos, gastos) y avisa qué comanda falta. ↻ gira 90° y vuelve a leer una foto.
Los recibos manuscritos necesitan el modelo local de Ollama; Tesseract solo lee impreso (instala el idioma `spa`).
