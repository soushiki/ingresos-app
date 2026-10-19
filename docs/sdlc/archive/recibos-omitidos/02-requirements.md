# 02 · Requisitos — M-13 recibos omitidos (aprobado 2026-10-18)

## Summary
- Meta: ningún recibo de una foto se pierde en silencio. Omitidos medidos por el OCR en la referencia de septiembre: 13/107 → **≤ 2/107**.
- Musts: **R1** «falta N» se anota desde ④ con la foto al lado · **R3** el nombre «85334-338 al 3341-343» se entiende (o avisa)
  · **R4** el informe de `medir` dice por qué se omitió cada recibo.
- NFR clave: todo local (qwen2.5vl, Tesseract, Real-ESRGAN); el escaneo de una foto no tarda más de +20 %.

## Stories
- **R1 (Must)** Como quien revisa el día, quiero anotar a mano un recibo que falta, para que no se pierda aunque el OCR no lo lea.
  - Dado el aviso «falta el 85388», cuando pulso «Anotar», entonces se abre el formulario manual con el número 85388 ya puesto y la foto
    de donde debía salir, entera, al lado.
  - Dado que lo guardo, entonces queda en el libro con `origen:"manual"` y el aviso de ese número desaparece.
  - Dado un número que de verdad no existe (anulado), cuando pulso «No existe», entonces el aviso se cierra y queda anotado el motivo.
- **R2 (Must)** Como quien cierra el día, quiero ver cuántos faltantes quedan sin resolver, para no exportar con huecos sin darme cuenta.
  - Dado 1+ faltantes abiertos, cuando exporto o cierro el día, entonces veo «quedan N recibos sin anotar» (aviso, no bloqueo).
- **R3 (Must)** Como quien nombra las fotos, quiero que nombres con el segundo número acortado («… al 3341-343») se entiendan,
  para que la foto se corte en tantos papeles como trae.
  - Dado «85334-338 al 3341-343», cuando se lee el nombre, entonces los números se completan con las cifras del primero (3341 → 85341)
    y `esperados` sale bien (la lista exacta se confirma contra la foto en diseño).
  - Dado un nombre que no se entiende, entonces ④ avisa «no entiendo el nombre de la foto X» en vez de cortar en 1 pieza callado.
- **R4 (Must)** Como quien mide, quiero que el informe guarde por pieza el número leído, el tipo y un trozo del texto, para saber si cada
  omitido es del corte, del número o del tipo.
  - Dado `medir_precision.py --completo`, entonces cada omitido del informe trae `causa` ∈ {corte, número, tipo}.
- **R5 (Should)** Como dueño, quiero que el número de cabecera se lea mejor (recortar arriba, ampliar ×2, leer solo dígitos) cuando el
  primer intento no lo da, para tener que anotar menos a mano.
  - Dada la referencia de septiembre, entonces omitidos medidos ≤ 2/107 y los otros números del informe M-12 no empeoran.
- **R6 (Should)** Como quien toma las fotos, quiero consejos cortos en el LEEME (fondo oscuro liso, una columna, cerca), sin obligar.
  - Dado el LEEME, entonces hay una sección «Cómo tomar la foto» de ≤ 8 líneas.
- **R7 (Could)** Lector por línea (Tesseract `image_to_data`, rearmar por filas) — solo si R5 no llega a la meta.
- **R8 (Could)** Separar una columna con 3 papeles (13/85582 → 85588).

## Non-functional
- **N1 Local:** ningún servicio externo; Google Vision no entra (fue un spike).
- **N2 Tiempo:** el escaneo de una foto sube como mucho +20 % frente a M-12; `medir --completo` sigue en minutos.
- **N3 Meta:** omitidos medidos (solo OCR, sin contar los anotados a mano) ≤ 2/107 en la referencia congelada (ADR 007).
- **N4 Sin regresión:** todas las `probar_*.py` pasan; aciertos y dudosos del informe M-12 no empeoran.
- **N5 Privacidad:** app en 127.0.0.1; las fotos y el libro no salen del equipo.

## Out of scope
- Servicios de OCR en la nube (Won't). · Obligar un formato de foto o rechazar fotos (Won't).
- Adivinar números de nombres con errores de digitación sin avisar (Won't). · Recibos Rappi (otro modelo de negocio).

## Decisiones (aprobadas 2026-10-18)
1. ¿Los anotados a mano cuentan para la meta? **No** — N3 mide solo el OCR; ④ muestra aparte cuántos se anotaron.
2. ¿R2 avisa o bloquea al exportar con faltantes? **Avisa**, no bloquea.
3. ¿+20 % de tiempo por foto es aceptable para R5? **Sí.**
