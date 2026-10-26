"""Texto que leería el OCR de papeles reales (recibos de venta, gastos de caja, factura de proveedor)."""

GASTO = """SU RESTAURANTE
PROPIETARIO DEL NEGOCIO
Nit: 123456789
CRA 36 # 48 - 27 Tel: 6434897
GASTO DE CAJA
Consecutivo : {n}
Responsable: CAJA
Fecha : 12/09/2026 11:51:14 p. m.
VALOR: ${v}
MEDIO PAGO :
FECHA DE ENTREGA 12/09/2026
Descripcion:
{d}
Firma: ____________"""
FOTO_PAPELES = "\n=== DOCUMENTO ===\n".join([
    GASTO.format(n=220, v="26,000", d="transportes de compras luis carmona"), "RECIBO DE CAJA MENOR\nVALOR: 26.000",
    GASTO.format(n=217, v="86,000", d="pago a domicilio pedro perez"), "RECIBO DE CAJA MENOR\nVALOR: 86.000\ncobro domicilio",
    GASTO.format(n=216, v="2,800", d="PAQUETE DE PILAS 3A"), "RECIBO DE CAJA MENOR\n2.800",
    """Transf
Sebastian Hernandez De la Espriella
CC. 1000000000
CRA 3 # 6-128 LOCAL 103B. Cartagena
Telefono: 6794109
SURTIMPRESIONES
Factura de venta de papel
N° POS67085
Fecha de emisión: 12/9/2026 1:50 am
Forma de pago: Contado
Método de pago: Efectivo
Vencimiento: 12/09/2026
Consumidor final
1 EXTRA TABL 10,000.00
Subtotal: $10,000.00
Total: $10,000.00
Total recibido: $10,000.00
Total de líneas: 1
Total de productos: 1"""])
VENTA = """>>===TURNO===> 13
GRACIAS POR SU COMPRA!
SU RESTAURANTE
PROPIETARIO DEL NEGOCIO
Nit: 123456789
CRA 36 # 48 - 27
Telefonos: 6434897
RECIBO #: 85531
ORIGINAL
Fecha de Venta: 12/09/2026 9:00:13 p.m.
NO RESPONSABLE DEL IMPTO AL CONSUMO
Mesa: M4
Mesero: YORLIN
Cliente: CONSUMIDOR FINAL
IDENTIFICACION: 22222222222
| Descripcion | Cant | Valor |
COMBO AMOR Y AMISTAD | 2 | 160,000
HEINEKEN | 3 | 18,000
SUBTOTAL CONSUMO $178,000
**TOTAL CONSUMO>> $178000
DESCUENTO $
*TOTAL A PAGAR> $178,000
PROPINA $17,800
PAGADO $195,800
PAGA CON CREDITO $95,800
PAGA CON EFECTIVO $100,000
CAMBIO $
>>===TURNO===> 36
GRACIAS POR SU COMPRA!"""
