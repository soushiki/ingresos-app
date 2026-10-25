"""Códigos del PUC (puc.com.co, Decreto 2650 de 1993): clase 1 dígito, grupo 2, cuenta 4, subcuenta 6; los dígitos 7–8 son auxiliares del negocio.
`puc_cuentas.json` es parcial (ver su campo «alcance»): un código fuera de lo bajado sale «sin verificar», nunca «no existe»."""
from __future__ import annotations
import json
from pathlib import Path

_P = json.loads(Path(__file__).with_name("puc_cuentas.json").read_text(encoding="utf8"))
NOMBRES: dict = _P["cuentas"]
_CON_SUB = set(_P["cuentas_con_subcuentas"])
_GRUPOS = {k[:2] for k in NOMBRES if len(k) == 4}


def nombre(codigo) -> str:
    """Nombre PUC más fino que exista para el código (subcuenta, cuenta, grupo o clase); "" si no hay."""
    c = str(codigo)
    return next((NOMBRES[c[:n]] for n in (6, 4, 2, 1) if c[:n] in NOMBRES), "")


def revisar(codigo) -> tuple[str, str]:
    """(estado, explicación). estado: «ok», «propia» (subcuenta del negocio en una cuenta sin subcuentas oficiales),
    «no existe» (la cuenta o la subcuenta no está en el PUC) o «sin verificar» (fuera de lo bajado)."""
    c = str(codigo).strip()
    if not (c.isdigit() and len(c) == 8): return "no existe", f"{c or '(vacío)'}: el código debe tener 8 dígitos (clase, grupo, cuenta, subcuenta y auxiliar)"
    if c[:2] not in _GRUPOS: return "sin verificar", f"{c}: el grupo {c[:2]} no está en la copia local del PUC"
    if c[:4] not in NOMBRES: return "no existe", f"{c}: la cuenta {c[:4]} no existe en el grupo {c[:2]} {NOMBRES.get(c[:2], '')} del PUC"
    if c[:4] not in _CON_SUB: return "sin verificar", f"{c}: no se bajaron las subcuentas de {c[:4]} {NOMBRES[c[:4]]}"
    oficiales = [k for k in NOMBRES if len(k) == 6 and k.startswith(c[:4]) and not k.endswith("99")]
    if c[:6] in NOMBRES: return "ok", f"{c}: {NOMBRES[c[:6]]} ({c[:4]} {NOMBRES[c[:4]]})"
    if not oficiales: return "propia", f"{c}: {c[:4]} {NOMBRES[c[:4]]} no trae subcuentas en el PUC; la {c[:6]} es del negocio"
    return "no existe", f"{c}: la subcuenta {c[:6]} no está en el PUC; {c[:4]} {NOMBRES[c[:4]]} tiene " + ", ".join(f"{k} {NOMBRES[k]}" for k in oficiales[:6]) + ("…" if len(oficiales) > 6 else "")


def puc_valida(cuenta, alias: dict | None = None, notas: dict | None = None) -> tuple[str, str, str]:
    """(cuenta, estado, aviso) · aplica primero el alias manual→PUC (`por_confirmar.json`, ADR-022) y luego `revisar`.
    estado: el de `revisar` sobre la cuenta final; aviso: «» o por qué se cambió o dudó. No decide la puente: eso lo hace el motor.
    notas: `alias_nota` del mismo JSON; su «estado» va en el aviso (sin nota → «por confirmar»)."""
    c = str(cuenta or "").strip(); aviso = ""
    destino = (alias or {}).get(c)
    nota = (notas or {}).get(c); est = nota.get("estado", "por confirmar") if isinstance(nota, dict) else "por confirmar"
    if destino and destino != c: aviso = f"{c} → {destino} (alias manual→PUC, {est})"; c = destino
    estado, expl = revisar(c)
    return c, estado, aviso or ("" if estado in ("ok", "propia") else expl)
