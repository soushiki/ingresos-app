# ADR-018 · Indra calcula giro e inclinación; la app gira la imagen con PIL

Estado: aceptado (2026-10-20, aprobado por el usuario)

## Contexto
R2 pide hojas derechas en 0/90/180/270° e inclinación final ≤ 1° entre −45° y +45°, sin regresión en 0°. En el spike, el trabajador devolvía la imagen ya girada en PNG (base64 de ida y de vuelta). `upright()` no está documentado en indra-ocr 1.1.2.

## Opciones
1. **El trabajador devuelve la imagen enderezada:** como el spike, pero manda la hoja completa dos veces por la tubería, y el recorte y el formato dependen de cv2 en el otro venv.
2. **El trabajador devuelve solo `{giro, incl}`** y la app aplica `rotate(-giro, expand)` y luego `rotate(incl, expand, fillcolor=blanco)` antes de `recortar`.

## Decisión
Opción 2. La regla de 0° es explícita: con `giro == 0` y `|incl| < 0,3°` la imagen no se toca, así los recortes y totales de v1.6.0 se mantienen. `_recortes(de_lado=True)` sigue votando 90/270 con el mismo `detectar`. Con Tesseract, `incl = 0.0` (igual que hoy). Las respuestas fuera de rango (giro ∉ {0,90,180,270} o |incl| > 45) cuentan como falla (ADR-017).

## Consecuencias
+ La respuesta pesa unos bytes, no una hoja, y la imagen se procesa en un solo sitio (la app).
− El fondo blanco con `expand` difiere del spike (`BORDER_REPLICATE`). Riesgo 2 del diseño: spike XS al empezar 5-implement.
− Dependemos de la forma de salida de `upright()` → la fijamos con `probar_indra.py`.

## Spike de fondo blanco (T5, 2026-10-20)
Fondo blanco con `rotate(expand, fillcolor blanco)` elegido: en 3 hojas a 8°/25°/45° la inclinación residual (perfil de proyección, sin Indra ni cv2 porque el venv del spike ya no existe) fue 0,00° (±0,25° de paso) igual que con BORDER_REPLICATE, y `recortar`+`separar` dieron los mismos recortes (1; sin `esperados`, comparación débil). Script: `spikes/indra_ocr/fondo.py`.

## Fitness tests
- `probar_motores.py`: con un `detectar` falso que devuelve `(0, 1.0, 0.2)`, `preparar_pagina` da los mismos bytes que con `(0, 0.0, 0.0)`. Mensaje: «ADR-018: hoja derecha modificada».
- `probar_indra.py` (solo si el venv existe): una imagen de prueba girada 90° y con 10° de inclinación vuelve con `giro == 90` y una inclinación de 10° ± 1° con el signo que la corrige. Mensaje: «ADR-018: upright() cambió de forma o de signo».
