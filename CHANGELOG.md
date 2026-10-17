# Changelog

## [1.0.1] — 2026-10-17
Arreglos menores del import de datos crudos y del chequeo de Host.

### Arreglado
- Importar datos crudos rechaza un papel con `valor` negativo (solo el cierre lleva negativos: faltante) (M-1).
- Importar datos crudos rechaza un día con dos papeles de igual `id` (M-2).
- Un Host con «@» (user@host) se rechaza con 403 aunque cambie la versión de Werkzeug (M-3).

## [1.0.0] — 2026-10-17
Primera versión con número. Documento soporte (Res. DIAN 167/2021) y app partida en dos PC.

### Libro contable (fase A)
- Hoja **DATOS OCR** (una fila por papel leído, con origen, estado y aviso) como primera hoja del Excel;
  **MOVIMIENTOS** se calcula desde ella con fórmulas (SUMIFS), así una corrección a mano se refleja.
- Cuentas puente para venta sin medio y gasto sin cuenta; hoja **AVISOS** (filas sin código, días que
  cambiaron desde que se confirmaron, efectivo 0 con propina/domicilio).
- Tope de propina + domicilio al efectivo; días con solo pendientes se guardan.

### Documento soporte (fase B)
- Proveedores no obligados a facturar (tipo/número/DV validados) y alias por tercero.
- Compras agrupadas por proveedor y semana (lun–dom) con fecha límite y estado (en plazo / vence pronto / vencida).
- Numeración reservada CTG 1–10000 en SQLite (`datos/soporte.db`), todo o nada; Excel con RESUMEN y una hoja por documento.
- Compra manual, transmitido (CUDS), anular con motivo, nota de ajuste (NA, contador aparte); días con documentos bloqueados.
- Pestaña ③ «Documento soporte».

### Dos PC (OCR separado)
- Exportar/importar **datos crudos (.json)** versionado con sha256 (ADR-004); informe nuevos/iguales/conflictos/bloqueados.
- `SIN_OCR=1`: la app arranca sin Ollama y ① ofrece «Importar datos». Guía `LEEME-contador.md`.

### Seguridad
- Host y Origin locales exigidos en toda la app (CSRF, DNS rebinding).
- Texto que empieza por `= + - @` se escribe como texto en los Excel (sin inyección de fórmulas).
- Topes de importación (|valor| ≤ 10^10, texto ≤ 20.000, ≤ 2.000 documentos por día, JSON anidado → 400).

### Arreglos
- Fechas OCR con año mal leído: si caen a más de 7 días del día, se usa la del día y se avisa.
- «Sin Texto» ya no aparece como proveedor; compras nuevas en una semana ya documentada se numeran aparte.
- Sin scroll lateral a 375 px en ①, ② y ③.
