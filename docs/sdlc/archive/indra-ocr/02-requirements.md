# 02 · Requisitos — M-25 Indra OCR  (aprobado 2026-10-20)

## Summary
- **Meta:** Indra OCR reemplaza a Tesseract como segundo lector R3 y como enderezador de hojas, corriendo local en su propio venv 3.14. Busca bajar omitidos de 5/103 a ≤ 2/103 sin empeorar totales. Sin Indra, la app vuelve a Tesseract (comportamiento v1.6.0) y lo avisa.
- **Musts:** R1 lector R3 con Indra · R2 enderezado con `upright()` · R4 respaldo a Tesseract con aviso · R6 instalador.
- **NFR clave:** todo offline después de la instalación (N3). Ninguna foto ni dato sale del PC.

## Stories
**R1 (Must): segundo lector con Indra.** Como cajero/dueño, quiero que el número del recibo y el total se confirmen con Indra, para que la nota «Sin confirmar por segundo lector» aparezca solo cuando de verdad falta algo.
- Dado el set congelado de 103 recibos, cuando corre R3 con Indra, entonces confirma el número verdadero en ≥ 75 recibos (Tesseract: 27) y el total verdadero en ≥ 96.
- Dado un recibo, cuando Indra lee el recorte, entonces sus números pasan por el mismo `_enteros` y por las mismas reglas de `validar.py` (no hay reglas nuevas).

**R2 (Must): enderezar hojas con Indra.** Como dueño, quiero que una hoja girada o inclinada se enderece sola, para no tener que volver a escanearla.
- Dadas las 20 hojas giradas 0/90/180/270°, cuando pasan por `preparar_pagina`, entonces las 20 quedan derechas en cada ángulo (cuentan como derechas las 2 hojas con recibos de lado).
- Dada una hoja inclinada entre −45° y +45°, cuando se endereza, entonces la inclinación que queda es ≤ 1°.
- Dada una hoja ya derecha, cuando se endereza, entonces los recortes y los totales leídos son los mismos que en v1.6.0 (sin regresión en 0°).

**R3 (Must): sin empeorar el resultado.** Como contador, quiero que el cambio no altere totales que hoy están bien.
- Dado el set congelado, cuando corre el bucle completo (qwen + R3 + R5) con `medir_precision`, entonces los totales correctos son ≥ los de v1.6.0 y los omitidos no suben.
- Meta: omitidos ≤ 2/103 (ver Q3).

**R4 (Must): respaldo a Tesseract con aviso.** Como cajero, quiero que la app siga funcionando si Indra no está o falla.
- Dado un PC sin el venv de Indra, cuando arranca la app, entonces R3 y el enderezado usan Tesseract como en v1.6.0 y la interfaz muestra «Indra no disponible: se usa Tesseract».
- Dado un trabajador que se cuelga o muere a mitad de una foto, cuando vence el tiempo límite, entonces se mata, se reinicia una vez, y si vuelve a fallar esa foto sigue con Tesseract (no se pierde la foto).
- `/api/contable/capacidades` informa qué motor está activo.

**R5 (Should): el trabajador no deja rastros.** Como dueño, quiero que cerrar la app cierre también a Indra, para no dejar 440 MB ocupados.
- Dada la app corriendo, cuando se cierra (normal o matando Flask), entonces el trabajador termina en ≤ 5 s (cierra al recibir EOF en stdin).
- Con el recargador de Werkzeug activo hay un solo trabajador (arranque perezoso, en el primer uso).

**R6 (Must): instalador de un paso.** Como dueño, quiero instalar Indra en cada PC con un solo script.
- Dado un PC con `py -3.14`, cuando corro el instalador, entonces crea el venv, instala `indra-ocr==1.1.2`, descarga los modelos una vez a `INDRA_OCR_MODEL_DIR` y termina con una prueba de humo («Indra listo»).
- Dado un PC sin `py -3.14`, cuando corro el instalador, entonces dice qué instalar y cómo (ver Q2), y la app sigue con Tesseract.
- Correrlo dos veces no rompe nada (idempotente).

**R7 (Should): versión protegida.** Como mantenedor, quiero una prueba que falle si `upright()` o el formato de salida de Indra cambian.
- Dado el trabajador, cuando corre `probar_indra.py`, entonces comprueba el saludo `ready`, un pedido de texto y un `upright()` en una imagen de prueba girada.

**R8 (Should): licencia leída.** Antes de publicar, leer una vez el texto completo de la licencia de los pesos y anotarlo en el runbook.

## Non-functional
- **N1 Velocidad:** R3 con Indra ≤ 0,2 s por recorte; enderezado ≤ 0,5 s por hoja; carga del modelo una sola vez por sesión (≈ 1 s). En ningún caso más lento que v1.6.0 por foto.
- **N2 Memoria:** un solo trabajador, ≤ 600 MB pico.
- **N3 Offline/privacidad:** después de la instalación no hay ningún intento de conexión (`HF_HUB_OFFLINE=1`; se verifica sin red). Las fotos viajan solo por la tubería local.
- **N4 Concurrencia:** un candado por pedido/respuesta; dos pedidos a la vez desde Flask no mezclan respuestas.
- **N5 Consistencia:** para la misma foto y la misma versión, Indra da la misma lectura (determinista).
- **N6 Compatibilidad:** la app sigue en Python 3.15; Indra en 3.14. Las pruebas `probar_*` existentes siguen pasando.

## Out of scope
- Indra como lector principal (qwen se queda; el spike mostró que Indra pierde ≈ 10 recibos más).
- Cambiar reglas de `validar.py` (salvo lo que decida Q1).
- Fotos con perspectiva o fondo de mesa (`separar` con fotos reales): otro ciclo.
- Mover la app a 3.14 o esperar ruedas cp315 (se revisa en 08).
- GPU, redistribuir los pesos de Indra.

## Open questions
- Q1 Los 3 dudosos falsos por ≈ 100 de Indra (8→6, cabecera vecina): ¿se deja la regla igual (van a ④ revisión)? **Decidido: sí**, dejarla y medir en 6-test.
- Q2 Instalador sin `py -3.14`: ¿solo avisar con el comando `winget install Python.Python.3.14`, o instalarlo él mismo? **Decidido: solo avisar.**
- Q3 Si el bucle completo no llega a ≤ 2/103 omitidos pero cumple R3 (no empeora): ¿se publica igual? **Decidido: sí**; la meta ≤ 2 es Should, «no empeorar» es Must.
