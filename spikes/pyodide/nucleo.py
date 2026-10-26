"""Spike: crudo (bytes) -> Excel del libro (bytes), mismo camino que importar en un PC vacío + ② Excel."""
import copy
from parser_module.contable.asientos import construir, CFG
from parser_module.contable.exportar import leer_crudo, libro_a_excel

def libro_desde_crudo(data: bytes, cfg: dict | None = None) -> bytes:
    dias, invalidos = leer_crudo(data)
    c = {"puente_ingreso": CFG["puente_ingreso"], "puente_gasto": CFG["puente_gasto"], **(cfg or {})}
    rs = {d["fecha"]: construir(d["fecha"], copy.deepcopy(d["documentos"]), d["banco"], c, d["cierre"], None) for d in dias}
    return libro_a_excel({k: r["filas"] for k, r in rs.items()}, c.get("negocio", ""), c.get("nit", ""), {k: r["datos"] for k, r in rs.items()}, [])
