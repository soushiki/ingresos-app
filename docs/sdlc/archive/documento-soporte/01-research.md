# 01 · Research — documento soporte (light, 2026-10-16)

## Summary
- Regla: un documento soporte por compra, o acumulado por proveedor y semana; se genera dentro de la semana siguiente a la primera operación. Fuera de plazo pierde efecto fiscal (INCP, Concepto DIAN 006942/2025). Hoy compilado en Res. Única DIAN 000227/2025.
- Contenido mínimo: título legal, fecha (= fecha de generación), nombre + NIT/ID del vendedor y del adquirente, descripción, valor total, consecutivo con prefijo/rango/vigencia autorizados por la DIAN. El CUDS y la firma los pone quien transmite, no la app.
- Emisión: la solución gratuita DIAN es de digitación manual; no se encontró carga masiva Excel/CSV. Tampoco se confirmó la importación en Vendty, Alegra ni Siigo (confianza baja). → La app genera un Excel/CSV propio y legible para transcribir, con columnas que imitan los campos del formulario DIAN.
- Código: Flask + JSON en `datos/` (sin DB), openpyxl. El tercero es solo un nombre (sin NIT/tipo ID) y no hay lógica de consecutivos: hay que crear un registro de proveedores y un contador de numeración.
- Pendiente para requisitos: rango de numeración real del usuario (prefijo, desde/hasta, vigencia), la regla de nota de ajuste y si contabilidad usa Vendty o la solución DIAN.

## Options compared
| Pregunta | Opción | Ajuste | Costo | Madurez | Veredicto |
|---|---|---|---|---|---|
| Salida | Excel por proveedor-semana + resumen (openpyxl) | Alto: ya está en el stack | Bajo | Probado en `exportar.py` | **Elegida** |
| Salida | XML UBL 2.1 firmado | Bajo: exige firma y transmisión | Alto | — | Fuera de alcance (triage) |
| Salida | Plantilla de importación de Vendty/Alegra/Siigo | Desconocido | Medio | Sin confirmar | Revisar luego si el proveedor da plantilla |
| Emisión | Solución gratuita DIAN (manual) | Bueno para pocos documentos | Gratis | Oficial | Destino probable de la transcripción |
| Emisión | Vendty | Emite documento soporte | Suscripción | Página comercial | Preguntar a contabilidad |
| Numeración | Contador local que valida rango y vigencia | Necesario | Bajo | — | **Elegida**: nunca reutilizar un número |

## Codebase map
- Entrada: `app.py` (Flask, puerto 5050; `python app.py` o `iniciar.bat`). Rutas contables en `app.py:209-343`, incluida `/api/contable/excel`.
- Datos: JSON en `datos/` (`historial`, `esquema`, `alias_negocio`, `libro`, `contable`). El NIT del negocio está en `datos/contable.json`.
- `parser_module/contable/`: `documentos.py` (venta, gasto_caja, factura; tercero como texto en L182-192), `asientos.py` (asientos y duplicados por número, L86-122; **tiene cambios sin commit**), `clasificar.py`, `exportar.py` (`libro_a_excel`, L17), `terceros_cuentas.json` (tercero → cuenta, sin NIT).
- Tests: scripts `probar_*.py` en la raíz, con checks `chk` por consola, sin pytest. Ejemplos en `parser_module/ejemplos/`.

## Risks / unknowns
- R1: el texto exacto de la Res. 167/2021 y de la 227/2025 no se leyó. Hay que verificar campos y plazos en el normograma DIAN antes del diseño.
- R2: la relación de la Res. 165/2023 con el documento soporte no está confirmada; parece ser una norma de facturación general.
- R3: no se sabe cómo se solicita la numeración. Confirmar con contabilidad el rango autorizado.
- R4: nota de ajuste: tiene número propio y no se puede reutilizar el original. ¿La app debe prepararla? Decidir en requisitos.
- R5: sin carga masiva, a muchos proveedores por semana la transcripción manual sale cara. Medir el volumen típico.
- R6: plazo semanal. La app debe avisar los documentos que estén cerca del límite.
- R7: los datos del proveedor (cédula, nombre, dirección) son datos personales y se guardan en local. Bajo riesgo, porque `exposed: no`.

## Sources
- https://micrositios.dian.gov.co/sistema-de-facturacion-electronica/lo-que-deberias-saber-soporte-adquisiciones-no-obligados/
- https://incp.org.co/publicaciones/infoincp-publicaciones/impuestos/2025/06/generar-el-documento-soporte-con-no-obligados-a-facturar-fuera-de-los-plazos-establecidos-invalida-su-efecto-fiscal/
- https://siemprealdia.co/colombia/impuestos/nota-de-ajuste-al-documento-soporte/
- https://normograma.invima.gov.co/normograma/docs/pdf/resolucion_dian_0167_2021.pdf
- https://normograma.invima.gov.co/normograma/docs/pdf/resolucion_dian_0165_2023.pdf
- https://legalytributarioenlinea.co.pwc.com/Repositorio%20PwC/PDF/Doctrina/DIAN/Conceptos/2024/CON-000206-24.pdf
- https://micrositios.dian.gov.co/sistema-de-facturacion-electronica/facturacion-gratuita-dian/
- https://www.dian.gov.co/impuestos/factura-electronica/Documents/Solucion-Gratuita-Proceso-de-generacion-documento-soporte-en-adquisiciones-efectuadas-a-no-obligados.pdf
- https://www.vendty.com/
- https://www.siigo.com/blog/tecnologia-innovacion/documento-soporte-para-los-no-obligados-a-facturar/
