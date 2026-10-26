"""ADR-026: el libro (crudo → días → extracto → Excel) en funciones puras, sin Flask ni disco.
Lo usan app.py (que guarda, bloquea y responde JSON) y la página del contador (Pyodide). Nada contable nuevo aquí:
el cálculo es `asientos.construir` (ADR-002) y el Excel `exportar.libro_a_excel`."""
from __future__ import annotations
import copy
from datetime import datetime
from .asientos import construir, CFG
from .exportar import libro_a_excel
from . import extracto as extr


def _ahora(ahora: str | None) -> str:
    return ahora or datetime.now().isoformat(timespec="seconds")


def cfg(c: dict | None = None) -> dict:
    "Config del libro: los puentes por defecto de asientos.CFG debajo de lo que traiga `c` (contable.json en la app; negocio/NIT en la página)."
    return {"puente_ingreso": CFG["puente_ingreso"], "puente_gasto": CFG["puente_gasto"], **(c or {})}


def dia(fecha: str, r: dict, banco: dict, cierre, extracto: list | None = None, ahora: str | None = None) -> dict:
    """extracto: las líneas guardadas del día (ADR-012); `r` ya debe venir calculado con ellas. Un día sin extracto no gana la clave."""
    return dict(fecha=fecha, documentos=r["documentos"], banco=banco, cierre=cierre or {}, cruces=r["cruces"], filas=r["filas"], pendientes=r["pendientes"], debito=r["debito"], credito=r["credito"],
                diferencia=r["diferencia"], guardado=_ahora(ahora), **({"extracto": extracto} if extracto else {}))


def dia_desde_crudo(d: dict, c: dict, extracto: list | None = None, ahora: str | None = None) -> dict:
    """ADR-004: un día del crudo recalculado con la config `c` de este PC (ADR-002); `extracto` = el que ya tenía el día, si lo había.
    Lanza la excepción de `construir` si un documento no se entiende (quien llama lo marca inválido)."""
    r = construir(d["fecha"], copy.deepcopy(d["documentos"]), d["banco"], c, d["cierre"], extracto)
    return dict(fecha=d["fecha"], documentos=r["documentos"], banco=d["banco"], cierre=d["cierre"], cruces=r["cruces"], filas=r["filas"], pendientes=r["pendientes"],
                debito=r["debito"], credito=r["credito"], diferencia=r["diferencia"], guardado=d["guardado"] or _ahora(ahora),
                importado=_ahora(ahora), **({"extracto": extracto} if extracto else {}))


def desde_crudo(dias: list, c: dict, ahora: str | None = None) -> tuple[dict, list]:
    "Como importar `leer_crudo(...)[0]` en un PC vacío: (libro, inválidos con motivo). Un día que no se puede calcular no entra."
    lib, invalidos = {}, []
    for d in dias:
        try: lib[d["fecha"]] = dia_desde_crudo(d, c, None, ahora)
        except Exception as e:  # noqa: BLE001  igual que cont_importar: el día no entra y se dice por qué
            invalidos.append(dict(fecha=d["fecha"], motivo=f"no se pudo calcular: {str(e)[:120]}"))
    return lib, invalidos


def facturas_cerca(lib: dict, tocados: dict, fecha: str, ventana: int) -> list:
    "ADR-015: documentos de los dias a +-ventana de `fecha` (el libro, con los dias en proceso encima)."
    d0 = extr._dia(fecha)
    if d0 is None: return []
    out = []
    for f, d in {**lib, **tocados}.items():
        d1 = extr._dia(f)
        if d1 is not None and abs((d1 - d0).days) <= ventana: out += d.get("documentos", [])
    return out


def facturas_usadas(lib: dict, tocados: dict, fecha: str) -> set:
    "FIX-3: factura_ids ya enlazadas o asignadas por lineas del extracto de OTROS dias."
    return {x["factura_id"] for f, d in {**lib, **tocados}.items() if f != fecha for x in d.get("extracto", []) if x.get("factura_id")}


def recalcular_dia(lib: dict, fecha: str, reglas: dict, memoria: dict, c: dict, ahora: str | None = None) -> dict:
    "Reclasifica el extracto del dia con la memoria y las facturas cercanas, lo reconstruye y lo deja en `lib`."
    d = lib[fecha]
    ext = extr.clasificar(d["extracto"], reglas, memoria, facturas_cerca(lib, {}, fecha, reglas["ventana_factura_dias"]), facturas_usadas(lib, {}, fecha))
    r = construir(fecha, d.get("documentos", []), d.get("banco", {}), c, d.get("cierre"), ext)
    lib[fecha] = dia(fecha, r, d.get("banco", {}), d.get("cierre"), ext, ahora)
    return lib[fecha]


def aplicar_extracto(lib: dict, lineas: list, reglas: dict, memoria: dict, c: dict, imp: str, ahora: str) -> tuple[dict, dict]:
    """ADR-012: reparte las líneas de `extr.leer_xlsx` por día (crea el día si falta), clasifica y recalcula solo los días con líneas nuevas.
    Deja esos días en `lib` (lo modifica) y devuelve (lib, resumen{nuevas, ya_estaban, por_revisar, dias, dias_creados})."""
    nuevas, ya, tocados = 0, 0, {}
    lib_antes = set(lib)
    for ln in lineas:
        d = tocados.get(ln["fecha"]) or copy.deepcopy(lib.get(ln["fecha"])) or dict(fecha=ln["fecha"], documentos=[], banco={}, cierre={})
        tocados[ln["fecha"]] = d
        if any(x.get("clave") == ln["clave"] for x in d.get("extracto", [])): ya += 1; continue
        d.setdefault("extracto", []).append(dict(ln, imp=imp)); nuevas += 1
    nuevos_dias = {}
    for fecha, d in tocados.items():
        if not any(x.get("imp") == imp for x in d.get("extracto", [])): continue   # nada nuevo: el día queda como estaba
        d["extracto"] = extr.clasificar(d["extracto"], reglas, memoria, facturas_cerca(lib, tocados, fecha, reglas["ventana_factura_dias"]), facturas_usadas(lib, tocados, fecha))
        r = construir(fecha, d.get("documentos", []), d.get("banco", {}), c, d.get("cierre"), d["extracto"])
        nuevos_dias[fecha] = {**d, "documentos": r["documentos"], "cruces": r["cruces"], "filas": r["filas"], "pendientes": r["pendientes"],
                              "debito": r["debito"], "credito": r["credito"], "diferencia": r["diferencia"], "guardado": ahora}
    lib.update(nuevos_dias)
    revisar = sum(1 for d in nuevos_dias.values() for x in d["extracto"] if x.get("imp") == imp and x.get("destino") == "revisar")
    return lib, dict(nuevas=nuevas, ya_estaban=ya, por_revisar=revisar, dias=sorted(nuevos_dias), dias_creados=sorted(f for f in nuevos_dias if f not in lib_antes))


def excel(lib: dict, c: dict, desde: str = "", hasta: str = "", avisos=()) -> bytes:
    """El Excel del libro entre desde y hasta (ISO, opcionales), recalculado con la config `c` de hoy (FIX-6).
    R9/ADR-002: filas y DATOS OCR salen del mismo cálculo; `avisos` se suman a los «cambió desde que se confirmó»."""
    lib = {k: v for k, v in lib.items() if (not desde or k >= desde) and (not hasta or k <= hasta)}
    rs = {k: construir(k, v.get("documentos", []), v.get("banco", {}), c, v.get("cierre"), v.get("extracto")) for k, v in lib.items()}
    dias, datos = {k: r["filas"] for k, r in rs.items()}, {k: r["datos"] for k, r in rs.items()}
    cambios = [f"{k}: cambió desde que se confirmó ({lib[k].get('guardado', 's/f')}): guardado débito {lib[k].get('debito', 0):,} · crédito {lib[k].get('credito', 0):,}; "
               f"hoy débito {r['debito']:,} · crédito {r['credito']:,}. Revisa el día o vuelve a confirmarlo".replace(",", ".")
               for k, r in sorted(rs.items()) if (lib[k].get("debito"), lib[k].get("credito")) != (r["debito"], r["credito"])]
    return libro_a_excel(dias, c.get("negocio", ""), c.get("nit", ""), datos, cambios + list(avisos))
