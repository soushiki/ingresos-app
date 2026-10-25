"""Libro contable: papeles (recibos de venta, gastos de caja, facturas) → documentos → asientos de débito y crédito."""
from .asientos import construir, abreviar_recibos, rangos, completar_desde_cierre
from .clasificar import Clasificador, Motor
from .documentos import MARCA, leer_texto, separar
from .exportar import libro_a_excel

__all__ = ["construir", "completar_desde_cierre", "abreviar_recibos", "rangos", "Clasificador", "Motor", "MARCA", "leer_texto", "separar", "libro_a_excel"]
