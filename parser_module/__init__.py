"""Módulo 2 · texto plano → campos del cierre de caja.

    from parser_module import parsear, Config
    cierre = parsear(texto, Config.cargar("alias_negocio.json"), anio=2026)
    cierre.campos["efectivo"].valor ; cierre.a_fila()
"""
from .campos import CAMPOS, CLAVES, NOMBRE
from .config import Config
from .esquema import Columna, Esquema
from .parser import Campo, Cierre, montos_del_texto, parsear

__all__ = ["parsear", "Config", "Cierre", "Campo", "CAMPOS", "CLAVES", "NOMBRE", "montos_del_texto", "Esquema", "Columna"]
