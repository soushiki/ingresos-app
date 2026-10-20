# 2 · Requisitos — cierre de caja (01c #2 + #4) · tamaño S

## Summary
- **Problema:** el día del libro suma solo los papeles leídos (01-09: el cierre supera a los papeles en ≈ 30 %) y el pasivo 2815 (28150501 domicilios, 28150502 propinas) solo recibe créditos, así que crece sin fin.
- **Comportamiento:** R1 si el cierre supera a los papeles, la diferencia de venta se registra (débito puente 13809501 / crédito 41401501) con aviso «cierre > papeles»; si los papeles superan al cierre, solo aviso, sin ajuste. R2 cada día con cierre debita 28150502 por las propinas del cierre y 28150501 por los domicilios pagados del cierre, con crédito a 11050501, restando lo que ya debitaron los vales «pago domicilios» de ese día (nunca dos veces). R3 rige al recalcular, con respaldo del libro antes.
- **Aceptación:** (a) dado 01-09, al recalcular el día suma el total del cierre en 4140 y la puente lleva la diferencia con los papeles, con aviso; (b) un día con papeles > cierre no cambia asientos y muestra aviso; (c) un día con vale «pago domicilios» de 50.000 y cierre de 50.000 debita 28150501 una sola vez; (d) cada día débito = crédito; (e) en septiembre recalculado el saldo de 2815 deja de crecer (≈ el de los días sin cierre).
- **Fuera de alcance:** extracto bancario (01c #5), filas sin código (#3), Rappi (#6), terceros (#7), pantallas nuevas, días sin cierre (quedan como hoy).
- **Riesgo:** leer mal el cierre (OCR) mete un ajuste falso al libro → el ajuste solo se aplica si el cierre se leyó con total y fecha; sale como aviso en la revisión y el respaldo permite volver atrás.

## Decisiones (aprobadas por el usuario 2026-10-19, valores por defecto)
1. ¿«Total pagado en domicilios» del cierre es lo que se paga a los domiciliarios ese día? [def.: sí; hoy `cruces` lo usa como «domicilios cobrados»]
2. ¿Las propinas se reparten al personal el mismo día, en efectivo y por el total (`propinas_total`)? [def.: sí, todo el mismo día desde caja 11050501]
3. ¿La diferencia cierre > papeles va a 41401501 (restaurante) aunque parte pueda ser domicilio/propina? [def.: sí, todo a 4140; el contador la reparte si hace falta]
