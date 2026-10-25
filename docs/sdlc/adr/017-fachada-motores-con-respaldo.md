# ADR-017 · Una fachada `motores` elige Indra o Tesseract, con las firmas de hoy

Estado: aceptado (2026-10-20, aprobado por el usuario)

## Contexto
R3 entra por `leer_digitos=` en `relectura.leer_recibo`, y el giro por `giro_automatico` en `orientacion`. R4 pide que sin Indra todo funcione como en v1.6.0 y que se avise. El requisito dice que no hay reglas nuevas en `validar.py` (Q1).

## Opciones
1. **Un `if indra` en cada sitio** (`app.py`, `orientacion.py`, `relectura.py`): el respaldo queda repartido y es fácil que un sitio se quede sin él.
2. **Cambiar `digitos.py` y `orientacion.py` por dentro:** mezcla dos motores en módulos que hoy son simples.
3. **Una fachada `ocr_module/motores.py`** con `leer_digitos(img)` y `detectar_giro(img)`. Cada llamada intenta con Indra y, si lanza `IndraNoDisponible`, usa la función de Tesseract de siempre. `orientacion` recibe `detectar=` igual que `relectura` recibe `leer_digitos=`.

## Decisión
Opción 3. El texto de Indra pasa por el mismo `digitos._enteros`. `validar.py` y `relectura.py` no se tocan. Si una llamada falla, solo esa foto usa Tesseract (no se pierde la foto). Con 2 fallas seguidas, el resto de la sesión va con Tesseract. `motores.estado()` alimenta `/api/contable/capacidades` (`motor`, `aviso`), y la interfaz muestra «Indra no disponible: se usa Tesseract».

## Consecuencias
+ El respaldo vive en un solo lugar, y las pruebas existentes siguen usando sus motores falsos.
+ `orientacion` se puede probar con un `detectar` falso.
− Una foto puede mezclar motores (Indra en un recorte, Tesseract en el siguiente) si falla a mitad. Se acepta: las reglas son las mismas.

## Fitness tests (`probar_motores.py`)
- Con `INDRA_VENV` apuntando a una carpeta vacía, `leer_digitos` devuelve lo mismo que `numeros_tesseract` y `estado()["motor"] == "tesseract"`. Mensaje: «ADR-017: sin Indra no volvió a Tesseract».
- Con un trabajador falso que muere a mitad de un pedido, esa llamada devuelve el resultado de Tesseract, no `None` ni una excepción. Mensaje: «ADR-017: foto perdida al caer Indra».
- `validar.py` y `relectura.py` no importan `motores` ni `indra`. Mensaje: «ADR-017: motor metido en las reglas».
