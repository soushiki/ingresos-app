# 02 · Requirements — M-26 Recuperar número con Indra (S)

## Summary
- **Problema:** con Indra como R3, 5/103 recibos Ascomp siguen omitidos por «número» (85334, 85375, 85389, 85390, 85411; informe `20261020-225729`): qwen no da el número y el paso R5 de cercanía (`relectura._cercano`, ADR-011) solo mira lo que leyó qwen (`numero` + `REC #` del texto), no lo que Indra vio en el recorte (Indra ve el número en 81/103).
- **Comportamiento (R1):** en el paso 4 de `leer_hoja`, si a una venta le falta el número y la foto trae faltantes del nombre (`completa`), los números que Indra leyó en ese recorte también cuentan como «leídos»: se asigna el **único** faltante igual (o a ≤ 1 cifra, mismo largo) a lo que vio Indra; 0 o ≥ 2 candidatos → no se asigna. La venta queda «dudoso» con el motivo «Número recuperado por el segundo lector (Indra leyó …): revísalo con la foto» y va a ④; un número ya usado por otra venta de la foto no se asigna. Sin Indra (respaldo Tesseract o sin segundo lector) se usa lo que dé ese lector, o nada cambia.
- **Aceptación (R2):** (a) tests de unidad en `probar_contable.py`: Indra ve el faltante → asignado + motivo; dos faltantes posibles → sin asignar; número ya tomado → sin asignar; sin faltantes o `completa=False` → sin cambios; (b) medir en la referencia de 103 (`medir_precision.py`): omitidos por «número» ≤ 2/103 y **0** números asignados distintos al real; las demás cifras del informe no empeoran; suite completa verde.
- **Fuera de alcance:** recibos Vendty (≈ nov. 2026), números de cierres/gastos/Rappi, cambiar qwen o el recorte, deps o motores nuevos (solo locales), pantallas nuevas (se reusa ④ y su motivo).
- **Riesgo:** un número equivocado es peor que uno omitido (el omitido se ve como «Falta N»). Mitigación: solo candidato único dentro de los faltantes del nombre, siempre «dudoso» para revisar, y la medición exige 0 malos; si no se llega a ≤ 2 sin malos, se publica lo que dé 0 malos y se anota la diferencia.

## Open questions
— (resuelta: el motivo queda como está en R1)
