# 06 · Test report — M-13 iteración 2 (T7–T9, e739d39..cae2ef0)

## Summary
- **FAIL (2 FIX)**: 18/18 `probar_*.py` en verde, pero la revisión encontró que R3 crea marcadores falsos con los nombres reales del escáner.
- Cobertura: R3 en probar_validar (+6: foto 3 = 85334, 85338–341, 85343 con aviso; basura → marcador) y probar_faltantes (marcador sin número);
  R4 en probar_precision (+7: `causa_de` tipo/corte/número; informe de septiembre: omitidos 42 = corte 25 + número 17 + tipo 0, la suma cuadra);
  R6 hecho a mano (LEEME §7, 6 líneas). R4 y R6 cumplen. R3 cumple el caso de la foto 3 y falla en los nombres sin números de recibo (FIX-3).
- No se ejecutaron: ataques (exposed: no), prueba de carga (I2 no fija ninguna NFR de latencia), lint (no hay ruff ni flake8).

## Failures
- Ninguna prueba falla.

## Review findings (diff e739d39..cae2ef0, revisado a mano)
1. **FIX-3 (R3, alto)**: el escáner nombra los PDF `comandas20261002_15584574.pdf`. Al quitar `comandas20261002_` quedan 8 cifras, así que
   `entendido=False` y cada PDF (y cada página, `…pdf#2`) crea un marcador «No entiendo el nombre». Son 11 de los 62 archivos de la referencia.
   Lo mismo pasa con `IMG_…`, `WhatsApp Image 2026-…` y `Scan 2026-…`. El usuario tendría que cerrar con «No existe» cada hoja escaneada.
   Además, ya antes de este cambio, `COMANDAS 2026-09-15.pdf` se leía como [2009, 2015, 2026], o sea faltantes falsos.
   Arreglo: `entendido=False` solo si el nombre **empieza** por un número de recibo (4–6 cifras) y aun así falla, como en
   `85490-492-501502-504-505.jpg`, que debe seguir dando marcador. Los nombres de fecha u hora (≥ 7 cifras seguidas, `AAAA-MM-DD`, o que empiezan
   por una palabra) dan `Nombre(None, [], True)`: no hay R5 y no hay marcador. probar_validar.py:58 hoy afirma lo contrario para `IMG_…` y hay que cambiarlo.
2. **FIX-4 (medio)**: un marcador «No entiendo» todavía abierto tiene `numero=""`, así que su clave es `None` en `_conservar_revisados`.
   Por eso, cada vez que se relee la foto se suma **otro** marcador abierto. Los que ya están en «No existe» sí los filtra `reconciliar`.
   Arreglo: la clave del faltante sin número es `("faltante", "", origen)`.
3. Menor, va para T10: `medir` compara `parent.name in ("comandas", "comanda")` distinguiendo mayúsculas, así que la carpeta `COMANDAS` se queda sin esperados.
   Para esos PDF no cambia nada (su nombre no trae números), pero los 25 «corte» son sobre todo PDF sin nombre útil y no son errores del corte.
   T10 debe leer `por_causa` con eso en mente.
4. Bien: `_por_sufijo` solo actúa fuera de rango y con ≥ 2 cifras. Los nombres de la referencia que ya se entendían dan lo mismo que antes (lo comprobé con los 62).
- Seguridad: no hay entradas nuevas por la red. El nombre se trata solo con regex sin retroceso catastrófico. Sin hallazgos.

## Debt
- +120/−32 líneas en 10 archivos, sin funciones nuevas de más de 20 líneas. Sin tarea DEBT.

## Smoke result (≈ 5 min, lo hace el usuario después de FIX-3/4; `python app.py` → http://127.0.0.1:5000/contable)
1. ① Escanea «3/comanda/85334-338 al 3341-343.jpg» → salen 6 recibos y el aviso «Nombre de la foto corregido: 3341 → 85341».
2. ① Escanea un PDF `comandas20261002_….pdf` → **ningún** marcador «No entiendo el nombre» en ④.
3. ① Escanea «10/comandas/85490-492-501502-504-505.jpg» → un marcador «No entiendo el nombre…» en ④ Faltan.
4. Vuelve a leer esa misma foto → sigue habiendo **un** solo marcador.
5. Abre LEEME §7 «Cómo tomar la foto» → se entiende en 30 s.
- Resultado: pendiente (se hace después de FIX-3/4).
