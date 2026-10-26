# 02 · Requirements — M-27 cuenta PUC por origen e ítem (aprobado, 2026-10-25)

## Summary
- **Meta:** la app pone la cuenta PUC a cada ítem de cada papel: primero por el origen del papel, luego por el contenido (palabras, proveedor), aprendiendo del manual; lo dudoso va a la cuenta puente y a revisión, con su motivo.
- **Top Musts:** R1 reglas por origen · R3 cuenta por ítem con reparto de la factura · R5 clasificador por capas que aprende del cuadro, sin deps nuevas.
- **NFR clave:** N1 acierto ≥ 85 % por ítem en sept–oct (entrenando con jun–ago), sin tocar nada que el usuario corrigió a mano (R7).
- Hallazgo (riesgo R1 de 01): hoy solo venta y Rappi sacan ítems con valor; la factura y el gasto no, y el cierre trae `gastos_detalle` (nombre, valor). R2 lo cubre.

## Stories
- **R1 (Must)** Como usuario, quiero que el origen del papel fije la cuenta cuando el origen basta, para no revisar lo obvio.
  - Dado una comanda/venta, cuando se clasifica, entonces el ingreso va a 41401501 y la contrapartida por medio (1105 efectivo, 1120 banco, 1305 fiado, 1345 tarjeta/Rappi, 2815 anticipo), con motivo «origen: comanda».
  - Dado un cierre, entonces efectivo → 1105 y lo bancario → 1120, por medio. Dado una línea del extracto, entonces se mantiene su regla de hoy (5315/4210/5305 y enlace a la factura).
- **R2 (Must)** Como usuario, quiero que la factura y el gasto de caja traigan sus ítems con valor, para poder repartirlos.
  - Dado una factura o vale con renglones «nombre … valor», cuando se lee, entonces `items` tiene cada renglón; los `gastos_detalle` del cierre se tratan como ítems.
  - Dado un papel sin ítems legibles, entonces se clasifica entero como un solo ítem (detalle + proveedor).
- **R3 (Must)** Como usuario, quiero que una factura con ítems de varias cuentas se reparta, para que cada gasto quede en su cuenta.
  - Dado una factura con ítems de 2+ cuentas, cuando se arma el asiento, entonces hay un débito por cuenta (suma de sus ítems) y un crédito, y débitos = créditos.
  - Dado ítems que no suman el total (OCR, propina, descuento), entonces la diferencia va a la puente con motivo «diferencia ítems vs total» y el papel queda en revisión.
- **R4 (Must)** Como usuario, quiero que cada cuenta sea una subcuenta o auxiliar válida del PUC, para que el contador no reciba códigos inventados.
  - Dado una cuenta propuesta, entonces existe en `puc_cuentas.json` (6 díg.) o es auxiliar de 8 díg. bajo una subcuenta oficial; si no, va a la puente.
  - Dado un uso del manual que no corresponde al PUC (513530 para gas/internet/teléfono → 513555/513535; 519575 para herramientas), entonces la app usa la subcuenta PUC y lo marca «por confirmar».
- **R5 (Must)** Como usuario, quiero que el motor aprenda del manual y diga por qué eligió cada cuenta, para confiar o corregir rápido.
  - Dado un ítem, entonces las capas van en orden: origen → enseñado → frases/léxico → léxico minado (palabra→cuenta, ≥ 2 veces, ≥ 80 %) → vecino más parecido (tolera «domcilios») → puente; el motivo dice la capa y la fuente («parecido a julio fila 631»).
  - Dado empate o confianza baja, entonces va a la puente (gasto 51959501 / ingreso 13809501) y a la cola de revisión.
- **R6 (Must)** Como usuario, quiero corregir la cuenta de un ítem y que la app lo recuerde, para no corregirlo dos veces.
  - Dado que cambio la cuenta de un ítem, entonces se guarda como «manual», se aprende (palabra y proveedor) y el siguiente ítem igual sale con esa cuenta, motivo «enseñado».
- **R7 (Must)** Como usuario, quiero reclasificar los días ya guardados sin perder mis correcciones.
  - Dado un mes guardado, cuando pulso «Reclasificar mes», entonces veo los cambios (antes → después) y solo se aplican si acepto; lo marcado «manual» nunca cambia.
  - Reclasificar dos veces da el mismo resultado (idempotente).
- **R8 (Must)** Como contador, quiero que el export traiga un renglón por cuenta de cada papel, para que «BALANCE x CTA» cuadre.
  - Dado un papel repartido, entonces el export trae un renglón por cuenta con el mismo número de papel, y el balance del mes sigue cuadrando con el de hoy en los papeles de una sola cuenta.
- **R9 (Should)** Como usuario, quiero un informe de acierto, para saber si el motor cumple N1.
  - Entrenando con jun–ago y probando con sept–oct: acierto global por ítem, acierto por cuenta y lista de fallos con su motivo.
- **R10 (Should)** Como contador, quiero la lista de lo «por confirmar» (las 8 decisiones del informe de inconsistencias + R4), para decidir una sola vez.
  - Un PDF/hoja con cada punto, la regla de mayoría usada y cuántos ítems afecta; al contestar, se cambia en un JSON, sin tocar código.

## Non-functional
- **N1 acierto** (ADR-025, antes 85 %): entrena jun–ago, prueba sept–oct, por ítem: ≥ 67 % de acierto y ≥ 85 % de precisión en lo decidido (piso de regresión); lo no decidido → puente + revisión; las cuentas con ≥ 10 ítems < 60 % salen en el informe R9 y en la lista del contador.
- **N2 sin deps nuevas:** solo stdlib y lo que ya está en `requirements.txt` (auditado, varios PC). Funciona sin internet.
- **N3 latencia:** clasificar un día < 1 s; reclasificar un mes (≈ 1.000 ítems) < 30 s en el PC del negocio.
- **N4 consistencia por operación:** guardar un papel/día = todo o nada (escritura atómica, como hoy); reclasificar un mes = por día, atómico, y se puede repetir si se corta; el informe R9 y la lista R10 pueden leer datos viejos.
- **N5 privacidad:** el extracto del cuadro que entra a `parser_module/contable/` (riesgo R6 de 01) lleva solo palabra, proveedor y cuenta: sin valores, fechas ni nombres de personas.
- **N6 trazabilidad (regulated):** cada cuenta lleva motivo y capa; el export no cambia de formato salvo el renglón por cuenta (R8).

### Valores de fuera (regulated)
| Valor | Fuente | Cambia |
|---|---|---|
| Códigos y nombres de clase→subcuenta (6 díg.) | Decreto 2650 de 1993, arts. 6–7 (`puc_cuentas.json`) | casi nunca |
| Auxiliares de 8 díg. y sus nombres | el negocio / el contador | al abrir una cuenta |
| Cuentas puente 51959501 / 13809501 | `contable.json`, el contador | rara vez |
| Las 8 decisiones «por confirmar» (1405 vs 1435, domicilios, Rappi, 513530, 519575…) | el contador | una vez, al contestar |
| Umbrales del léxico minado (≥ 2, ≥ 80 %) y de confianza | internos (no legales) | al medir N1 |

## Out of scope (Won't)
- sklearn/rapidfuzz (solo plan B de N1). NIT por tercero (M-19), soporte por gasto (M-20), impoconsumo (M-21).
- Vendty/Ascomp export. Recuperar número con Indra (M-26). Cambiar las reglas del extracto (R1 solo las respeta).
- Inventario por ítem (1405/1435 queda como cuenta, no como kárdex).

## Open questions
Ninguna. Aprobado por el usuario el 2026-10-25 con los defaults: Q1 meta N1 = 85 % por ítem; Q2 diferencia ítems vs total → puente + revisión; Q3 reclasificar con botón por mes y vista previa.
