# 02 · Requisitos — vocabulario de medio de pago (01c #8) · S

## Summary
- **Problema:** la columna `medio` del libro y de DATOS OCR mezcla valores (Nequi, Daviplata, Rappi, Datáfono, Mixto, «(sin medio)»…) y los asientos que no son de caja también llevan medio; el manual usa 8 valores y deja vacío lo que no mueve caja.
- **Comportamiento:** todo asiento usa solo `Efectivo / Transferencia / Bre-B / QR / PSE / Tarjeta / Crédito personal / App`; los asientos sin caja (2815, puentes 13809501/51959501, ajustes) quedan con medio vacío. Se normaliza al leer y al recalcular; el libro viejo se corrige solo al recalcular (sin migración).
- **Chequeo de aceptación:** R1–R4 abajo, en un test nuevo + recalcular septiembre: ningún valor de `medio` fuera de los 8 + vacío.
- **Fuera de alcance:** cambiar cuentas PUC, valores o descripciones; pantallas nuevas; migrar archivos viejos.
- **Riesgo:** perder el detalle «Nequi/Daviplata» si alguien lo usaba para cuadrar el extracto → se conserva en la descripción del asiento.

## Stories
- **R1** Como contador, quiero que el libro y DATOS OCR solo muestren los 8 medios (o vacío) para filtrar y sumar por medio sin limpiar a mano.
  - Dado un recibo leído con «Nequi», «Daviplata» o «transf», cuando se genera el libro, entonces `medio = Transferencia`.
  - Dado «Datáfono»/«visa» → `Tarjeta`; «Rappi» → `App`; «llave» → `Bre-B`.
- **R2** Como contador, quiero que los asientos que no mueven caja tengan medio vacío, como el manual.
  - Dado un asiento a 2815, a una cuenta puente o un ajuste, cuando se genera el libro, entonces `medio = ""`.
  - Dada una venta sin medio leído, DATOS OCR muestra `medio` vacío (el aviso «corrige el medio» se queda).
- **R3** Como contador, quiero que un pago «Mixto» no aparezca como medio.
  - Dada una venta mixta, se reparte por medio (ya pasa hoy) y ninguna fila dice «Mixto».
  - Dada una factura de gasto mixta, el asiento toma el medio del mayor valor pagado y sigue el aviso «revisa el medio».
- **R4** Como usuario, quiero que un libro guardado antes de v1.5 se vea normalizado al recalcular, sin migrar nada.
  - Dado un día viejo con «Nequi» en `medio`, cuando se recalcula, el Excel sale con `Transferencia`.

## Non-functional
- Un solo mapa de sinónimos (en `normalizacion.json`/`MEDIOS`), no reglas repartidas; valores desconocidos → vacío + aviso, nunca se inventan.
- Las 18 suites existentes siguen verdes.

## Out of scope
- Separar Nequi/Daviplata como medios propios; cambiar `RECAUDO_DESC` (las descripciones conservan «Nequi»).
- Migrar libros/Excel ya exportados.

## Open questions
Ninguna. Decididas 2026-10-19 (aprobado por el usuario): Nequi/Daviplata → `Transferencia`; factura «Mixto» → medio del mayor valor + aviso; valor no reconocido → vacío + aviso.
