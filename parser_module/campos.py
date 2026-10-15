"""Los 12 campos del cierre de caja y el vocabulario base (se amplía con alias_negocio.json)."""

# (clave, nombre en Excel, tipo)  tipo: "monto" = dinero · "conteo" = cantidad
CAMPOS = [
    ("total", "Total vendido", "monto"),
    ("ordenes", "Número de órdenes", "conteo"),
    ("anuladas", "Facturas anuladas", "conteo"),
    ("propinas", "Propinas", "monto"),
    ("base", "Base", "monto"),
    ("cortesia", "Cortesía", "monto"),
    ("transf", "Transferencias", "monto"),
    ("efectivo", "Efectivo", "monto"),
    ("rappi", "Rappi", "monto"),
    ("cajam", "Caja menor", "monto"),
    ("domicilio", "Domicilio", "monto"),
    ("descontar", "Descontar", "monto"),
]
NOMBRE = {k: n for k, n, _ in CAMPOS}
TIPO = {k: t for k, _, t in CAMPOS}
CLAVES = [k for k, _, _ in CAMPOS]

# alias (sin tildes, minúsculas) -> peso de confianza (1 = inequívoco; <0.75 obliga a revisión)
ALIAS_BASE = {
    "total": {"total vendido": 1, "total venta": 1, "total ventas": 1, "venta total": 1, "ventas totales": 1,
              "total dia": 1, "total del dia": 1, "venta del dia": 1, "ventas del dia": 1, "gran total": 0.9,
              "t vendido": 1, "vendido": 0.9, "ventas": 0.85, "venta": 0.85, "total": 0.8},
    "ordenes": {"numero de ordenes": 1, "num ordenes": 1, "n ordenes": 1, "no ordenes": 1, "# ordenes": 1,
                "cant ordenes": 1, "cantidad de ordenes": 1, "ordenes": 1, "orden": 0.9, "numero de pedidos": 1,
                "pedidos": 0.95, "# pedidos": 1, "# ord": 1, "n ord": 1, "ord": 0.8, "tickets": 0.8,
                "comandas": 0.8, "numero de facturas": 0.9, "mesas": 0.7, "cuentas": 0.7, "facturas": 0.6},
    "anuladas": {"facturas anuladas": 1, "factura anulada": 1, "fact anuladas": 1, "fact anul": 1, "anuladas": 1,
                 "anulada": 1, "anulacion": 0.95, "anulaciones": 0.95, "anul": 0.85, "devueltas": 0.7},
    "propinas": {"propinas": 1, "propina": 1, "prop": 0.85, "tips": 0.95, "servicio": 0.7, "voluntario": 0.7},
    "base": {"base": 1, "base caja": 1, "base inicial": 1, "base de caja": 1, "sencillo": 0.85,
             "sencillo inicial": 0.9, "fondo": 0.7},
    "cortesia": {"cortesia": 1, "cortesias": 1, "cort": 0.9, "regalo": 0.7, "regalos": 0.7, "obsequio": 0.7,
                 "obsequios": 0.7},
    "transf": {"transferencias": 1, "transferencia": 1, "transf": 1, "trans": 0.8, "nequi": 0.9, "daviplata": 0.9,
               "bancolombia": 0.9, "pse": 0.85, "banco": 0.75, "bancos": 0.75, "consignacion": 0.7, "bre b": 0.85},
    "efectivo": {"efectivo": 1, "efec": 1, "efe": 0.8, "cash": 0.9, "plata": 0.6},
    "rappi": {"rappi": 1, "rapi": 1, "rappy": 1, "rp": 0.8},
    "cajam": {"caja menor": 1, "c menor": 1, "cmenor": 1, "caja m": 0.9, "gastos caja menor": 1,
              "gastos": 0.7, "gasto": 0.6},
    "domicilio": {"domicilios": 1, "domicilio": 1, "domi": 1, "domis": 1, "dom": 0.85},
    "descontar": {"descontar": 1, "a descontar": 1, "descuentos": 0.9, "descuento": 0.9, "desc": 0.9,
                  "restar": 0.8, "deducir": 0.8},
}

# Alias que son solo UNA PARTE de un campo: si aparece el total del campo, se ignoran; si solo hay partes, se suman.
PARTES_BASE = {"transf": {"nequi", "daviplata", "bancolombia", "pse", "bre b"}}

# Palabras que solo matizan a otra etiqueta ("Total efectivo"): se descartan si van pegadas a otra etiqueta.
MODIFICADORES = {"total"}
