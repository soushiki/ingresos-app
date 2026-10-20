# 02 · Requisitos — extracto bancario (01c #5) · M

## Summary
- **Meta:** subir el Excel del extracto de Bancolombia y que cada línea quede con concepto y cuenta PUC. Cada línea genera su asiento contra 11200501 en el libro y en el Excel. Lo dudoso queda en una lista para que el usuario elija la cuenta.
- **Musts:** R1 importar sin duplicar · R2 concepto automático · R4 las ventas por banco no se cuentan dos veces · R5 asientos de salidas con la cuenta elegida y recordada.
- **NFR clave:** el libro nunca queda a medias (todo o nada por importación). Las cuentas y tasas reguladas viven en JSON editable, no en el código.

## Stories
- **R1 (Must)** Como usuario, quiero subir el .xlsx del extracto (hoja «Hoja 1»: Fecha | Descripción | Referencia | Valor) para no digitar movimientos.
  - Dado el archivo de septiembre (513 líneas), cuando lo subo, entonces veo 513 movimientos con fecha (solo el día, sin la hora 05:00) y el valor con signo.
  - Dado que subo después el 1–30 sept. (se cruza con 1–23), cuando importo, entonces solo entran las líneas nuevas. La clave es (fecha, descripción, referencia, valor, n.º de ocurrencia) y el resumen dice «N nuevas, M ya estaban».
  - Dado un archivo con otras columnas, otra hoja o un ZIP, cuando lo subo, entonces sale un error claro y no se guarda nada.
- **R2 (Must)** Como usuario, quiero que cada línea tenga su concepto (GMF, RECAUDO QR, PAGO LLAVE, ABONO VISA/MASTER/AMEX, PAGO RAPPI, RENDIMIENTOS, TRANSFER CR, TRANSFER NEQUI CR, PAGO PSE, PAGO QR, COMPRA…). Así veo de un vistazo qué es cada una.
  - Dada la hoja MOVIMIENTOS (etiquetada a mano) como oráculo, cuando clasifico «Hoja 1», entonces ≥98 % de las líneas coinciden. Las que no coinciden salen en el reporte del test (por los errores de la hoja: TRABSFER, etc.).
  - Las reglas son una tabla ordenada en JSON (prefijo anclado + signo). Una línea que no encaja en ninguna queda «SIN CONCEPTO» y va a la lista de revisión. Nunca se descarta.
- **R3 (Should)** Como usuario, quiero ver los totales del mes por concepto para cuadrar contra el extracto.
  - Dado septiembre importado, entonces la suma por concepto coincide con los totales de MOVIMIENTOS (salvo las líneas mal etiquetadas allí), y la suma de todo = suma de la columna Valor.
- **R4 (Must)** Como contador, quiero que las ventas que entran por banco (QR, llave, tarjetas, Nequi, transferencias, PSE) no queden dos veces en el libro.
  - Dado un día con casillas «banco» digitadas y el extracto importado, cuando se genera el libro, entonces cada recaudo aparece una sola vez (ver P1).
  - Dado que casilla y extracto no cuadran en un día, entonces se muestra la diferencia por medio y no se suma nada en silencio.
- **R5 (Must)** Como usuario, quiero elegir la cuenta de cada salida dudosa (TRANSFERENCIA CTA SUC VIRTUAL, TRANSF A <nombre>, A NEQUI, PSE…). Quiero que la app recuerde la elección por tercero para no repetirla cada mes.
  - Dada una salida sin cuenta, entonces aparece en una lista de revisión (como ④) con fecha, descripción y valor, y un selector de cuenta del plan.
  - Dado que asigno «TRANSF A ANA PRUEBA» → 5105xx, cuando importo el mes siguiente, entonces esa línea ya sale con 5105xx y marcada «recordada». Se puede cambiar.
  - Mientras no elijo, el asiento va a la cuenta puente 51959501 (como hoy con los gastos sin cuenta) y el día queda con pendiente.
- **R6 (Must)** Como contador, quiero que las líneas automáticas generen asiento sin preguntar: GMF → 53152001, rendimientos → 42100505, pago Rappi → contra la cuenta por cobrar 13452501 (v1.4.0); abono de tarjeta → por el neto (P3).
  - Dado un cobro de 4x1000, entonces débito 53152001 y crédito 11200501 por el valor exacto del extracto (no se recalcula la tasa).
  - Dado un abono de rendimientos, entonces débito 11200501 y crédito 42100505.
- **R7 (Should)** Como usuario, quiero que las líneas con signo raro (crédito «COMPRA», débito «VENTAS», ≈8 en sept.) queden marcadas para revisar.
  - Dada una de esas líneas, entonces va a la lista de revisión con el aviso «signo inesperado».
- **R8 (Must)** Como contador, quiero que los asientos del extracto salgan en el Excel del libro como los demás (fecha, código, nombre, tercero, descripción, débito, crédito, medio, grupo).
  - Dado septiembre importado y revisado, cuando exporto, entonces cada día cuadra (débito = crédito) y las filas del banco llevan grupo «Extracto».
- **R9 (Could)** Como usuario, quiero borrar una importación entera si subí el archivo equivocado.
  - Dada una importación, cuando la deshago, entonces el libro vuelve a quedar como antes de esa importación.

## Non-functional
- **Consistencia por operación:** importar es todo o nada (se escribe libro.json una vez, al final, con copia previa). Revisar/asignar una cuenta guarda línea por línea. Recalcular el libro es determinista: el mismo extracto + las mismas elecciones dan las mismas filas.
- **Latencia:** importar y clasificar un mes (≈650 líneas) < 3 s. Guardar una elección < 300 ms.
- **Privacidad:** el extracto (nombres de terceros, valores) se queda local en `datos/`. No se manda a ningún servicio. La app sigue en 127.0.0.1.
- **Trazabilidad:** cada asiento del banco guarda la clave de la línea del extracto que lo originó.
- **Regulado (valores externos, en JSON editable):**
  | Valor | Fuente | Cambia |
  |---|---|---|
  | GMF 4x1000 (0,4 %): solo se registra lo que cobró el banco | Ley 1111/2006, ET art. 871 | rara vez (reforma) |
  | 50 % del GMF deducible en renta | ET art. 115 | rara vez; lo maneja el contador, la app no lo calcula |
  | Cuentas PUC (53152001, 42100505, 5105/5120/5135, 13452501, 530515) | manual del contador | cuando el contador lo diga |
  | Retención arriendo 3,5 % / base 10 UVT | ET, DUR 1625/2016 | UVT cada año |

## Out of scope (Won't, v1)
- Leer PDF o fotos del extracto (no OCR), ZIP con clave, otros bancos.
- Calcular retenciones (arriendo, rendimientos) o la comisión de tarjetas. Se registra lo que dice el extracto (ver P3).
- Clasificador por ML; conciliación automática factura ↔ pago.
- Conexión directa al banco (API).

## Decisiones (usuario, 2026-10-20)
- **P1:** el extracto llena solo las casillas «banco» de cada día. Si ya había un número digitado y no cuadra, se muestra la diferencia por medio (R4).
- **P2:** se empieza con las cuentas del manual en un JSON editable, marcadas «por confirmar». El contador las ajusta después sin tocar el código.
- **P3:** los abonos de tarjeta se registran por el neto del extracto. La comisión 530515 queda fuera de v1.

## Open questions
- (contabilidad, no bloquean) nómina 2505 vs 5105; ¿PSE a la pasarela de pagos = publicidad o plataforma?; retención en rendimientos.
