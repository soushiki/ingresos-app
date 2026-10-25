"""T10 (M-27, R7, ADR-021): reclasificar un mes guardado en dos pasos. `plan` = vista previa de los cambios de cuenta por ítem + huella;
`aplicar` recalcula el plan, y solo si la huella coincide rehace los días con `construir`. Lo `manual` nunca cambia (S2) y repetir no cambia nada.
Solo compras (factura, gasto de caja, caja menor): ventas, Rappi y cierre van por origen (R1) y su cuenta no mueve el asiento."""
from __future__ import annotations
import copy, hashlib, json, shutil
from datetime import datetime
from pathlib import Path
from .asientos import construir

VERSION = "1.8.0"   # respaldo libro.antes-v1.8.0.json (S3) y rastro de cada reclasificación
COMPRAS = ("factura", "gasto_caja", "caja_menor_manuscrito")


class HuellaDistinta(ValueError):
    """El libro o el motor cambiaron desde la vista previa (S1): hay que pedir el plan de nuevo."""


def _de_cero(doc: dict) -> dict:
    """Copia del papel lista para clasificar otra vez: los ítems no manuales pierden cuenta y capa (conservan nombre y valor);
    un papel viejo sin ítems pierde su cuenta salvo que la eligiera el usuario (cuenta_manual)."""
    d = copy.deepcopy(doc)
    if d.get("items"):
        for it in d["items"]:
            if not it.get("manual"): it.update(cuenta="", capa="", conf=0.0, motivo="")
    elif not d.get("cuenta_manual"): d["cuenta"] = ""
    return d


def _dias(lib: dict, mes: str, motor) -> tuple:
    """→ (cambios, {fecha: documentos reclasificados}) de los días del mes con al menos un cambio de cuenta."""
    cambios, nuevos = [], {}
    for fecha in sorted(k for k in lib if k.startswith(mes + "-")):
        docs, hubo = [], False
        for doc in lib[fecha].get("documentos", []):
            if doc.get("tipo") not in COMPRAS: docs.append(doc); continue
            previo = {i: str(it.get("cuenta") or "") for i, it in enumerate(doc.get("items") or [])}
            nuevo = motor.clasificar_doc(_de_cero(doc))
            for i, it in enumerate(nuevo["items"]):
                antes = previo[i] if i in previo else str(doc.get("cuenta") or "")     # ítems rehechos (FIX-2) o papel viejo: la del papel
                antes, despues = antes or motor.puente, str(it["cuenta"]) or motor.puente      # "" = la puente (aviso «falta cuenta»)
                if antes == despues: continue
                hubo = True
                cambios.append(dict(fecha=fecha, doc_id=doc.get("id", ""), numero=doc.get("numero", ""), tipo=doc["tipo"], tercero=doc.get("tercero", ""),
                                    item=it.get("nombre", ""), valor=int(it.get("valor") or 0), antes=antes, despues=despues, capa=it.get("capa", ""), motivo=it.get("motivo", ""),
                                    duplicado=doc.get("contar") is False))     # copia de otro papel (dup_de): se reclasifica igual, pero no va a los libros
            docs.append(nuevo)
        if hubo: nuevos[fecha] = docs
    return cambios, nuevos


def _huella(lib: dict, mes: str, cambios: list) -> str:
    guardado = {k: lib[k].get("guardado", "") for k in sorted(lib) if k.startswith(mes + "-")}
    return hashlib.sha256(json.dumps(dict(mes=mes, cambios=cambios, guardado=guardado), ensure_ascii=False, sort_keys=True).encode("utf8")).hexdigest()


def _rehacer(dia: dict, fecha: str, docs: list, cfg: dict) -> dict:
    return construir(fecha, docs, dia.get("banco") or {}, cfg, dia.get("cierre"), dia.get("extracto"))


def _totales(filas: list) -> dict:
    """Como la cabecera del libro (contable.html): ingresos = Σ (crédito − débito) de cuentas 4, gastos = Σ (débito − crédito) de cuentas 5."""
    c = lambda f: str(f.get("codigo") or "")[:1]
    return dict(debito=sum(f.get("debito", 0) for f in filas),
                ingresos=sum(f.get("credito", 0) - f.get("debito", 0) for f in filas if c(f) == "4"),
                gastos=sum(f.get("debito", 0) - f.get("credito", 0) for f in filas if c(f) == "5"))


def plan(lib: dict, mes: str, motor, cfg: dict | None = None) -> dict:
    """mes «2026-09». No toca `lib`. → {mes, cambios:[{fecha, doc_id, numero, tipo, tercero, item, valor, antes, despues, capa, motivo}],
    resumen: {cuenta: {antes, despues}} (Σ valor que sale/entra por cuenta, para la tabla antes → después), huella}.
    El resumen deja fuera duplicados y ítems de $0: no mueven plata en los libros.
    Con `cfg`, `dias` = los días cuyo débito o ingresos cambian al rehacerlos con `construir` (como hará `aplicar`, también por reglas
    nuevas de otros ciclos), con {fecha, antes, despues} de {debito, ingresos, gastos}: el usuario lo ve antes de Aplicar."""
    cambios, nuevos = _dias(lib, mes, motor)
    dias = []
    for fecha, docs in (nuevos.items() if cfg is not None else ()):
        antes, despues = _totales(lib[fecha].get("filas") or []), _totales(_rehacer(lib[fecha], fecha, docs, cfg)["filas"])
        if (antes["debito"], antes["ingresos"]) != (despues["debito"], despues["ingresos"]): dias.append(dict(fecha=fecha, antes=antes, despues=despues))
    resumen = {}
    for c in cambios:
        if c["duplicado"] or not c["valor"]: continue
        resumen.setdefault(c["antes"], dict(antes=0, despues=0))["antes"] += c["valor"]
        resumen.setdefault(c["despues"], dict(antes=0, despues=0))["despues"] += c["valor"]
    return dict(mes=mes, cambios=cambios, resumen=resumen, dias=dias, huella=_huella(lib, mes, cambios))


def aplicar(lib: dict, vista: dict, motor, cfg: dict, ahora: str | None = None) -> dict:
    """Recalcula el plan de `vista["mes"]`; si su huella ≠ la de la vista levanta HuellaDistinta y no cambia nada (S1).
    → libro nuevo (no muta `lib`) con los días que cambian rehechos por `construir` y un rastro `reclasificaciones[]` en cada uno (S3).
    El rastro va por día porque las claves del libro son fechas. Guardar es aparte (`guardar`), en una sola escritura."""
    mes = vista.get("mes", "")
    cambios, nuevos = _dias(lib, mes, motor)
    if not mes or _huella(lib, mes, cambios) != vista.get("huella"): raise HuellaDistinta("el libro cambió desde la vista previa; vuelve a pedirla")
    ahora = ahora or datetime.now().isoformat(timespec="seconds")
    out = dict(lib)
    for fecha, docs in nuevos.items():
        dia = lib[fecha]
        r = _rehacer(dia, fecha, docs, cfg)
        rastro = dict(fecha_hora=ahora, version=VERSION, cambios=[{k: c[k] for k in ("doc_id", "item", "valor", "antes", "despues")} for c in cambios if c["fecha"] == fecha])
        out[fecha] = dict(dia, documentos=r["documentos"], cruces=r["cruces"], filas=r["filas"], pendientes=r["pendientes"], debito=r["debito"], credito=r["credito"],
                          diferencia=r["diferencia"], guardado=ahora, reclasificaciones=[*dia.get("reclasificaciones", []), rastro])
    return out


def guardar(ruta, lib: dict, version: str = VERSION):
    """Una escritura atómica (tmp + replace). Antes de la primera, copia única `libro.antes-v<version>.json` (S3); no se pisa."""
    ruta = Path(ruta); resp = ruta.with_name(f"libro.antes-v{version}.json")
    if ruta.exists() and not resp.exists(): shutil.copy2(ruta, resp)
    tmp = ruta.with_suffix(".tmp"); tmp.write_text(json.dumps(lib, ensure_ascii=False, indent=1), encoding="utf8"); tmp.replace(ruta)
