# ADR-016 · Indra en un trabajador persistente del venv 3.14, por JSON por líneas

Estado: aceptado (2026-10-20, aprobado por el usuario)

## Contexto
onnxruntime no tiene ruedas cp315 y la app corre en 3.15 (N6). Cargar el modelo toma ≈ 0,9 s y el trabajador ocupa ≈ 440 MB. Flask atiende pedidos en varios hilos, y el recargador de Werkzeug importa la app dos veces.

## Opciones
1. **Un proceso por foto:** simple, pero +0,9 s de carga por foto y otro pico de memoria cada vez.
2. **Pasar la app a 3.14:** quita la tubería, pero hay que rehacer el entorno de todos los PC.
3. **Un trabajador persistente** en `indra_venv` (`python -I`), JSON por líneas en stdin/stdout, arrancado en el primer uso.

## Decisión
Opción 3. El cliente (`ocr_module/indra.py`) lo arranca en el primer pedido (no al importar, así el recargador no crea dos). Espera `ready` hasta `INDRA_ARRANQUE_S` y protege cada pedido/respuesta con un candado con tope. Si vence `INDRA_TIMEOUT_S`, mata el proceso y lo reinicia una vez. Con 2 fallas seguidas, Indra queda apagado por esa sesión (ADR-017). stderr va a `logs/indra.log`, y cierra con `quit` → `wait(5)` → `kill`, más `atexit`. El trabajador también sale cuando le llega EOF en stdin (si Flask muere de golpe). Usa `CREATE_NO_WINDOW` y `shell=False`.

## Consecuencias
+ La carga se paga una vez por sesión, y el proceso de la app no carga nada de ONNX.
− Hay más código de proceso (tiempos límite, reinicio) y hace falta un trabajador falso para probarlo.
− Un solo trabajador: los pedidos van en fila. Alcanza de sobra para la carga estimada (< 10 % ocupado).

## Fitness tests (`probar_motores.py`)
- Ningún archivo de la app (fuera de `indra_worker.py`) importa `indra_ocr`, `onnxruntime` ni `cv2`. Mensaje: «ADR-016: la app cargó Indra en su proceso».
- Importar `app` no arranca ningún proceso (se cuenta con un `Popen` falso). Mensaje: «ADR-016: el trabajador arrancó al importar».
- Un trabajador falso que no contesta se mata y se reinicia dentro de `INDRA_TIMEOUT_S` + 1 s. Mensaje: «ADR-016: trabajador colgado sin reiniciar».
- Al cerrar stdin del trabajador falso, termina en ≤ 5 s. Mensaje: «ADR-016: trabajador huérfano».
