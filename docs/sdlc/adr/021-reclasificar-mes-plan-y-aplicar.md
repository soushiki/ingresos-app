# ADR-021 · Reclasificar un mes en dos pasos (plan con huella → aplicar), sin pisar lo manual

Estado: aceptado (2026-10-25, aprobado por el usuario)

## Contexto
R7 pide reclasificar los días guardados con vista previa, sin cambiar nada de lo marcado «manual», y que repetirlo dé lo mismo. N4 pide que sea atómico y que se pueda repetir si se corta. El libro es un solo `libro.json` (1,7 MB al mes) que se escribe con tmp + replace. Los ítems no se guardaron hasta hoy, pero el `texto` sí.

## Opciones
1. **Reclasificar al abrir cada día**: es invisible para el usuario y cambia el balance sin que lo acepte.
2. **Un botón que aplica directo**: no tiene vista previa (falla R7).
3. **`plan(lib, mes)`**: vuelve a sacar los ítems del `texto` guardado si faltan, clasifica, y devuelve los cambios más una huella (sha256 de los cambios y de la `guardado` de cada día). **`aplicar(lib, plan)`** recalcula el plan y, si la huella coincide, rehace los días con `construir` y escribe el libro **una sola vez**.

## Decisión
Opción 3. Los ítems con `manual: true` (y los papeles con `cuenta_manual`, por migración al leer) se saltan. Antes de la primera escritura se guarda el respaldo `libro.antes-v1.8.0.json`, y se agrega `reclasificaciones[]` al libro como rastro.

## Consecuencias
+ Lo que se ve es lo que se aplica (S1). Un corte deja el libro viejo intacto, y se puede repetir.
+ Una sola escritura por mes: más simple que una por día y más fuerte que lo que pide N4.
− Si se guarda un día entre el plan y el aplicar, la huella cambia y hay que pedir la vista previa de nuevo (se acepta).

## Fitness tests (`probar_reclasificar.py`)
- Después de `aplicar(plan(lib))`, un `plan` nuevo da 0 cambios. Mensaje: «ADR-021: reclasificar no es idempotente».
- Un ítem `manual` con cuenta X sigue en X después de aplicar, aunque el motor diga Y. Mensaje: «ADR-021: se pisó una corrección manual».
- Con la huella alterada, `aplicar` falla y no escribe. Mensaje: «ADR-021: se aplicó un plan distinto a la vista previa».
