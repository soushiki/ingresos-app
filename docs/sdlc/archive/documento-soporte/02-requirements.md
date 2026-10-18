# 02 · Requisitos — documento soporte (APROBADO, 2026-10-16)

## Summary
- Meta: con las compras a proveedores no obligados a facturar que ya registra la app, preparar un documento soporte por proveedor y semana, numerado con CTG 1–10000, en un Excel listo para transcribir a la solución gratuita DIAN. La app no firma ni transmite.
- Must principales: R10 + R9 primero (nada se descarta en silencio y lo mal leído se corrige en DATOS OCR), luego R1 registro de proveedores, R3 acumulado proveedor-semana con consecutivo que nunca se repite y R5 Excel para transcribir.
- Orden (usuario, 2026-10-16): R9 y R10 se terminan antes de generar el documento soporte final, para que las compras estén completas y corregidas.
- NFR clave: un número de documento usado nunca se reutiliza, ni tras un error o un reinicio (N1).

## Stories
- R1 (Must): Como contador, quiero registrar una vez a cada proveedor no obligado (tipo y número de ID, nombre, dirección, municipio, correo opcional) para no volver a digitarlo.
  - Dado un tercero nuevo en una compra, cuando lo marco «no obligado», entonces la app pide sus datos y los guarda en `datos/`.
  - Dado un proveedor sin tipo o número de ID, cuando intento incluirlo en un documento, entonces la app lo bloquea y dice qué falta.
- R2 (Must): Como usuario, quiero que el nombre de tercero que lee el OCR se asocie a un proveedor del registro, para que las compras de un mismo proveedor se junten.
  - Dado «Sin Texto», «Proveedor» u otro encabezado leído como tercero, entonces la app no lo acepta y pide elegir un proveedor.
  - Dado un alias ya asociado, cuando aparece otra vez, entonces se asigna solo al proveedor.
- R3 (Must): Como contador, quiero agrupar las compras de cada proveedor por semana (lunes a domingo) en un documento con el siguiente número CTG libre.
  - Dadas 3 compras del mismo proveedor en la semana, cuando genero, entonces sale 1 documento con 3 líneas y el total correcto.
  - Dado el último número usado CTG-57, cuando genero 2 documentos, entonces reciben CTG-58 y CTG-59.
  - Dado que el rango llegó a 10000, entonces la app no numera y avisa que hay que pedir un rango nuevo.
- R4 (Must): Como usuario, quiero digitar a mano una compra que el OCR no tiene (p. ej. pagada por transferencia), para que entre al documento soporte.
  - Dado el formulario de compra manual con proveedor, fecha, descripción y valor, cuando guardo, entonces queda en el acumulado de su semana.
- R5 (Must): Como contador, quiero un Excel con una hoja por documento y una hoja resumen, con columnas en el orden del formulario DIAN, para transcribir sin buscar datos.
  - Dados documentos generados, cuando descargo, entonces cada hoja tiene número, fecha de generación, datos del adquirente (NIT del negocio) y del proveedor, líneas y total.
  - La hoja resumen trae número, proveedor, semana, total, fecha límite y estado.
- R6 (Must): Como contador, quiero ver qué semanas están cerca del plazo o ya vencidas, para no perder el efecto fiscal.
  - Dada una semana cuya primera compra fue hace 6 días o más sin documento, entonces la app la marca «vence pronto» con la fecha límite.
  - Dada una semana fuera de plazo, entonces la marca «vencida» y no la numera sin que el usuario lo confirme.
- R7 (Must): Como contador, quiero marcar un documento como «transmitido» (con el CUDS opcional), para que la app no lo vuelva a generar ni a cambiar.
  - Dado un documento transmitido, cuando se edita una de sus compras, entonces la app lo impide y ofrece una nota de ajuste.
- R8 (Should): Como contador, quiero preparar una nota de ajuste sobre un documento transmitido, con su propio número, para corregirlo.
  - Dado CTG-58 transmitido, cuando creo una nota de ajuste por −20.000, entonces sale con número propio, referencia a CTG-58 y el valor ajustado.
- R9 (Must, previo): Como usuario, quiero que el Excel del libro traiga la hoja «DATOS OCR» (una fila por papel: archivo, estado, aviso) y que MOVIMIENTOS se calcule desde ella con fórmulas, para ver y corregir a mano lo mal leído.
  - Dado un valor corregido en DATOS OCR, cuando abro el Excel, entonces MOVIMIENTOS y los totales cambian sin macros.
- R10 (Must, previo): Como usuario, quiero que las facturas y recibos sin valor o sin medio de pago entren a una cuenta puente con aviso, en vez de descartarse, y que no se exporten filas sin código de cuenta (01c puntos 1 y 3).
  - Dada una factura de compra sin valor leído, entonces aparece en la lista de pendientes y no queda fuera en silencio.

## Non-functional
- N1 Numeración: el contador se guarda en disco antes de entregar el Excel (escritura atómica). Un número asignado nunca se libera, ni si se borra el documento; un número anulado queda en el resumen como «anulado».
- N2 Trazabilidad: cada línea del documento guarda la compra de origen (archivo OCR o «manual»).
- N3 Privacidad: los datos de proveedores solo se guardan en local en `datos/` (`exposed: no`) y no se envían a ningún servicio.
- N4 Volumen: hasta ~50 documentos al mes, generados en menos de 5 s.
- N5 Pruebas: un script `probar_documento_soporte.py` con checks `chk`, igual que los demás.

### Valores externos (regulated: yes)
| Valor | Fuente | Cambia |
|---|---|---|
| Prefijo CTG, rango 1–10000 | Autorización de numeración DIAN del negocio | Al pedir un rango nuevo (configurable) |
| Vigencia de la numeración: 2 años | Res. 000167/2021, compilada en Res. 000227/2025 | Se asume vigente; sin fecha en la app |
| Plazo: dentro de la semana siguiente a la primera operación | Res. 000167/2021, art. 1.6.1.4.12 DUR 1625; Concepto DIAN 006942/2025 | Con una nueva resolución |
| Campos mínimos del documento | Res. 000167/2021, compilada en Res. 000227/2025 | Con una nueva resolución; verificar en diseño (riesgo R1 de 01) |

## Out of scope
- Firmar, generar el CUDS o el XML UBL, y transmitir a la DIAN.
- Extracto bancario automático (01c punto 5): en la v1 las compras por transferencia se digitan (R4).
- Retención en la fuente sobre el documento soporte, salvo que diseño encuentre que el formulario DIAN la exige.
- Plantillas de importación de Vendty, Alegra o Siigo.
- Los cambios 2, 4, 6, 8 y 9 de 01c (cierre de caja, propinas, Rappi, medio de pago, días de más).

## Open questions
- Q1 resuelta: R9 y R10 entran como Must y van antes del documento soporte (usuario, 2026-10-16).
- Q2 (se asume): semana de lunes a domingo.
- Q3 (se asume): la nota de ajuste usa un contador aparte con prefijo y rango configurables; confirmar con contabilidad.
