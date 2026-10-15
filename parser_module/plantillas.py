"""Plantillas de columnas listas para usar."""
from __future__ import annotations


def _c(clave, nombre, sin=(), tipo="monto", **kw):
    return {"clave": clave, "nombre": nombre, "tipo": tipo, "sinonimos": list(sin), **kw}


def recibo_pos() -> dict:
    """Recibo «CIERRE DE CAJA RESUMIDO» del punto de venta: valores base + ganancia/pérdida de caja."""
    cols = [
        _c("base_caja", "Base de caja", ["base de caja"]),
        _c("venta_efectivo", "Venta en efectivo", ["total venta en efectivo"]),
        _c("tarjetas_sin_prop", "Tarjetas (sin propina)", ["total tarjetas sin prop"]),
        _c("tarjetas_con_prop", "Tarjetas (con propina)", ["total tarjetas con prop"]),
        _c("transferencias", "Transferencias / App", ["transferencia"]),
        _c("propinas_efectivo", "Propinas en efectivo", ["propinas en efectivo"]),
        _c("propinas_tarjeta", "Propinas por tarjeta", ["propinas por tarjeta"]),
        _c("propinas_app", "Propinas con app", ["total propinas con app"]),
        _c("propinas_total", "Total propinas", ["total propinas"]),
        _c("dom_vendido", "Domicilios vendidos", ["total vendido en domicilios"]),
        _c("dom_numero", "Nº de domicilios", ["total numero de domicilios"], tipo="conteo"),
        _c("dom_pagado", "Domicilios pagados", ["total pagado en domicilios"]),
        _c("ingresos_caja", "Otros ingresos de caja", ["total ingresos"]),
        _c("gastos_caja", "Gastos de caja", ["total gastos"]),
        _c("efectivo_esperado", "Efectivo esperado en caja", ["total efectivo en caja"], ocurrencia=1),
        _c("efectivo_contado", "Efectivo contado (cajero)", ["efectivo regis cajero", "efectivo registrado cajero"]),
        _c("faltante_impreso", "Faltante / sobrante impreso", ["faltante", "sobrante"], negativo=True),
        _c("diferencia", "Ganancia / Pérdida de caja", tipo="calculo", resultado=True,
           formula="[Efectivo contado (cajero)] - [Efectivo esperado en caja]"),
    ]
    return {
        "columnas": cols,
        "controles": [
            {"nombre": "El faltante impreso no coincide con contado − esperado",
             "formula": "[Faltante / sobrante impreso] - [Ganancia / Pérdida de caja]", "tolerancia": 1},
            {"nombre": "Tarjetas sin propina + propinas por tarjeta ≠ tarjetas con propina",
             "formula": "[Tarjetas (sin propina)] + [Propinas por tarjeta] - [Tarjetas (con propina)]", "tolerancia": 1},
            {"nombre": "Propinas (efectivo + tarjeta + app) ≠ total propinas",
             "formula": "[Propinas en efectivo] + [Propinas por tarjeta] + [Propinas con app] - [Total propinas]", "tolerancia": 1},
        ],
        # renglones del recibo que NO son columnas y no deben confundirse con ellas
        "ignorar": ["total ingresos con app", "total ingresos con app efe", "total venta efect", "tot efect caja sin base",
                    "total credito personal", "total abonos", "propinas por credito personal"],
        "opciones": {"vacio_cero": True, "notas": False},
    }


def cierre_manual() -> dict:
    """Las 12 columnas del cierre de caja manuscrito (la plantilla original)."""
    from .campos import CAMPOS
    return {"columnas": [_c(k, n, tipo=t) for k, n, t in CAMPOS], "controles": [], "ignorar": [],
            "opciones": {"vacio_cero": False, "notas": True}}


def restaurante_pyg() -> dict:
    """Plantilla MÍNIMA para cierres de caja de restaurante: solo lo necesario para ganancias y pérdidas.
    Ventas por medio de pago + gastos + faltante/sobrante, y el resultado del día (impreso si el recibo lo trae; si no, calculado)."""
    from .lexico import DIFERENCIA, RESULTADO
    cols = [
        _c("venta_efectivo", "Venta en efectivo", ["total venta en efectivo", "venta en efectivo", "ventas en efectivo",
                                                  "ventas efectivo", "venta efectivo", "efectivo ventas", "efectivo venta", "ventas de efectivo", "ventas de contado", "venta de contado"]),
        _c("venta_tarjeta", "Venta con tarjetas", ["total tarjetas", "total tarjetas sin prop", "ventas con tarjeta", "venta con tarjeta",
                                                  "ventas por tarjeta", "venta por tarjeta", "ventas tarjeta", "venta tarjeta", "total datafono",
                                                  "+credito", "+debito", "+tarjeta credito", "+tarjeta debito", "+tarjetas credito", "+tarjetas debito"]),
        _c("venta_transf", "Venta por transferencias / app", ["transferencia", "transferencias", "total ingresos con app", "pagos con app",
                                                             "ventas por transferencia", "ventas por app", "+nequi", "+daviplata", "+bancolombia", "+pse", "+rappi"]),
        _c("ventas_impresas", "Ventas totales (impresas)", ["total ventas", "ventas totales", "venta total", "total vendido", "ventas del dia",
                                                           "venta del dia", "ventas netas", "venta neta", "total ventas del dia"]),
        _c("gastos", "Gastos / egresos", ["total gastos", "gastos", "gasto", "total egresos", "egresos", "salidas de caja", "salidas",
                                         "gastos de caja", "gastos del dia", "caja menor", "compras", "pago a proveedores", "pagos a proveedores"]),
        _c("domiciliarios", "Pago a domiciliarios", ["total pagado en domicilios", "pagado en domicilios", "pago domiciliarios",
                                                    "pago a domiciliarios", "pagos domicilios", "pago domicilios"]),
        _c("faltante_sobrante", "Faltante / sobrante de caja", sorted(DIFERENCIA), negativo=True),
        _c("resultado_impreso", "Ganancia / pérdida (impresa)", sorted(RESULTADO), negativo=True),
        _c("ventas_dia", "Ventas del día", tipo="calculo",
           formula="si0([Ventas totales (impresas)], [Venta en efectivo] + [Venta con tarjetas] + [Venta por transferencias / app])"),
        _c("resultado", "Ganancia / pérdida del día", tipo="calculo", resultado=True,
           formula="si0([Ganancia / pérdida (impresa)], [Ventas del día] - [Gastos / egresos] - [Pago a domiciliarios] + [Faltante / sobrante de caja])"),
    ]
    suma = "[Venta en efectivo] + [Venta con tarjetas] + [Venta por transferencias / app]"
    return {
        "columnas": cols,
        "controles": [{"nombre": "Las ventas impresas no coinciden con la suma por medio de pago",
                       "formula": f"si0([Ventas totales (impresas)], {suma}) - ({suma})", "tolerancia": 1000}],
        # renglones que se parecen a una columna pero NO lo son (o son ambiguos) → se descartan en silencio
        "ignorar": ["total tarjetas con prop", "total ingresos con app efe", "total venta efect prop", "total venta",
                    "total vendido en domicilios",
                    "total credito personal", "propinas por credito personal"],
        "opciones": {"vacio_cero": True, "notas": False},
    }


PLANTILLAS = {"restaurante_pyg": ("Restaurante · ganancias y pérdidas (mínima)", restaurante_pyg),
              "recibo_pos": ("Recibo POS «Cierre de caja resumido»", recibo_pos),
              "cierre_manual": ("Cierre de caja manuscrito (12 columnas)", cierre_manual)}
