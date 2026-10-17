"""Excel con tu estructura: una hoja «MOVIMIENTOS <MES>» por mes (mismas columnas y colores) y una hoja «RESULTADO»."""
from __future__ import annotations
import io
from collections import defaultdict
from datetime import date
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter as L

MESES = ["ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO", "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"]
HEAD = ["Fecha", "Código cuenta contable", "Nombre cuenta contable", "Tercero", "Descripción", "Movimiento débito", "Movimiento crédito", "", "Reporta", "Medio de Pago"]
VERDE, ROSA, AZUL = "E2EFDA", "FCE4D6", "D9ECFC"
_f = lambda c: PatternFill("solid", fgColor=c)
FINO = Border(bottom=Side(style="hair", color="BFBFBF"))


DATOS_HEAD = {"fecha": "Fecha", "archivo": "Archivo de origen", "tipo": "Tipo", "numero": "Número", "tercero": "Tercero", "detalle": "Detalle", "valor": "Valor",
              "medio": "Medio de pago", "cuenta": "Cuenta", "estado": "Estado", "aviso": "Aviso", "propina": "Propina", "domicilio": "Domicilio", "bloque": "Asiento", "id": "Id"}
AMARILLO = "FFF2CC"


def texto(c):
    """FIX-12 (CWE-1236): texto libre (papel leído, digitado) que empieza por = + - @ queda como texto, no como fórmula activa."""
    if isinstance(c.value, str) and c.value[:1] in ("=", "+", "-", "@", "\t", "\r"): c.data_type = "s"; c.quotePrefix = True
    return c


D = "'DATOS OCR'!"
DC = {k: L(i) for i, k in enumerate(DATOS_HEAD, 1)}   # columna de cada campo en DATOS OCR
NOTAS_DATOS = ["Los importes de MOVIMIENTOS son fórmulas sobre la hoja DATOS OCR: corrige allí un valor, una cuenta o un estado y el libro se recalcula al abrirlo en Excel.",
               "Solo suman las filas con estado «ok». Si corriges una cuenta o un medio que no tiene fila en MOVIMIENTOS (un grupo nuevo), ese valor no entra: corrígelo en la app y vuelve a exportar.",
               "La propina y el domicilio de cada venta van como valor fijo: si corriges el valor de una venta, corrige también su propina y su domicilio."]


def _criterio(v) -> str:
    """Criterio literal de SUMIFS: comodines escapados y un «=» delante si el texto empieza con un operador (ADR-002: nunca una celda vacía)."""
    s, op = str(v), ""
    if s.startswith("<>"): s, op = s[2:], "<>"
    s = s.replace("~", "~~").replace("*", "~*").replace("?", "~?")
    if not op and s[:1] in ("<", ">", "="): op = "="
    return '"' + (op + s).replace('"', '""') + '"'


def formula(fx, fila: int, ref_fila, ref_dato) -> str:
    """fx de asientos.construir → texto de la fórmula (sin «=»). ref_fila(j) y ref_dato(i) dan la celda (o el valor) de otra fila del día o de DATOS OCR."""
    op, *a = fx
    if op == "sum":
        col, crit = a
        pares = [(DC["fecha"], f"$A{fila}"), (DC["estado"], '"ok"')] + [(DC[k], _criterio(v)) for k, v in crit.items()]
        return f"SUMIFS({D}{DC[col]}:{DC[col]}," + ",".join(f"{D}{c}:{c},{x}" for c, x in pares) + ")"
    if op == "dato": return ref_dato(a[0])
    if op == "fila": return ref_fila(a[0])
    t = [formula(x, fila, ref_fila, ref_dato) for x in a]
    if op == "min": return f"MIN({','.join(t)})"
    if op == "+": return "+".join(t) if len(t) > 1 else t[0]
    if op == "-": return t[0] + "".join(f"-({x})" if "+" in x or "-" in x else f"-{x}" for x in t[1:])
    raise ValueError(f"fx desconocido: {op}")


def hoja_datos(wb, datos: dict) -> dict:
    """DATOS OCR (R9, ADR-002), primera hoja: una fila por papel y medio de pago. Lo que no está «ok» o trae aviso va en amarillo.
    Devuelve {fecha: fila de la hoja donde empieza ese día} para que MOVIMIENTOS apunte a sus datos."""
    ws = wb.create_sheet("DATOS OCR"); ws.append(list(DATOS_HEAD.values())); inicio = {}
    for c in ws[1]: c.font = Font(bold=True); c.fill = _f(AZUL); c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for f in sorted(datos):
        inicio[f] = ws.max_row + 1
        for r in datos[f]:
            ws.append([date.fromisoformat(r["fecha"]) if k == "fecha" else (int(r[k]) if k == "cuenta" and str(r[k]).isdigit() else (r[k] if r[k] != "" else None)) for k in DATOS_HEAD])
            k = ws.max_row; ws.cell(k, 1).number_format = "dd/mm/yyyy"
            for c in ws[k]: texto(c)
            for i in (7, 12, 13): ws.cell(k, i).number_format = '$ #,##0;-$ #,##0;"$ -"'
            if r["estado"] != "ok" or r["aviso"]:
                for c in ws[k]: c.fill = _f(AMARILLO)
    for i, w in enumerate([12, 40, 14, 10, 26, 30, 14, 16, 11, 12, 36, 12, 12, 10, 10], 1): ws.column_dimensions[L(i)].width = w
    ws.freeze_panes = "A2"; ws.auto_filter.ref = f"A1:{L(len(DATOS_HEAD))}{max(ws.max_row, 2)}"
    return inicio


def libro_a_excel(dias: dict, negocio: str = "", nit: str = "", datos: dict | None = None, avisos: list | None = None) -> bytes:
    """dias: {'2026-09-12': [fila, …]} con filas de asientos.construir(); datos: {'2026-09-12': construir()['datos']} para la hoja DATOS OCR.
    Con datos, cada importe es una fórmula sobre DATOS OCR (ADR-002); filas y datos de un día deben salir del mismo construir().
    avisos: líneas extra para la hoja AVISOS (p. ej. días que cambiaron desde que se confirmaron)."""
    wb = Workbook(); wb.remove(wb.active)
    inicio = hoja_datos(wb, datos) if datos else {}
    por_mes, avisos = defaultdict(list), list(avisos or [])
    for f in sorted(dias):
        for j, x in enumerate(dias[f]):   # R10: una fila sin código de cuenta no entra a MOVIMIENTOS; se avisa
            if str(x.get("codigo") or "").strip(): por_mes[f[:7]].append(dict(x, _j=j))
            else: avisos.append(f"{f}: fila sin código de cuenta ({x.get('descripcion') or x.get('nombre') or 's/d'}, débito {x.get('debito') or 0:,}, crédito {x.get('credito') or 0:,}); no se exportó".replace(",", "."))
    hojas = []
    for ym in sorted(por_mes):
        y, m = int(ym[:4]), int(ym[5:7]); nom = f"MOVIMIENTOS {MESES[m - 1]}"; hojas.append((nom, y, m))
        ws = wb.create_sheet(nom); filas = por_mes[ym]; ult = max(f["fecha"] for f in filas)
        ws["A2"] = "Balance de prueba por tercero"; ws["A3"] = negocio or "(nombre del negocio)"; ws["A4"] = f"NIT {nit}" if nit else "(NIT)"
        ws["A5"] = f"A {int(ult[8:]):d} de {MESES[m - 1].capitalize()} de {y}"
        for r in (2, 3): ws[f"A{r}"].font = Font(bold=True)
        n = len(filas); ult_fila = 8 + n
        ws["E7"] = "Total del mes"; ws["E7"].font = Font(bold=True); ws["E7"].alignment = Alignment(horizontal="right")
        ws["F7"] = f"=SUM(F9:F{ult_fila})"; ws["G7"] = f"=SUM(G9:G{ult_fila})"; ws["I7"] = "=F7-G7"
        for c in ("F7", "G7", "I7"): ws[c].number_format = '$ #,##0;[Red]-$ #,##0'; ws[c].font = Font(bold=True)
        for i, h in enumerate(HEAD, 1):
            c = ws.cell(8, i, h or None); c.font = Font(bold=True); c.fill = _f(AZUL); c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        ws.row_dimensions[8].height = 32
        filas = sorted(filas, key=lambda x: (x["fecha"], 0))   # sorted es estable: conserva el orden de cada día
        pos = {(f["fecha"], f["_j"]): (k, f) for k, f in enumerate(filas, 9)}
        def ref_fila(fe, j):   # celda del importe de otra fila del mismo día (contrapartida); si no se exportó, su valor
            k, g = pos.get((fe, j), (None, dias[fe][j]))
            lado = (g.get("fx") or ["debito"])[0]
            return f"{'G' if lado == 'credito' else 'F'}{k}" if k else str(g[lado] or 0)
        for k, f in enumerate(filas, 9):
            imp = [f["debito"] or 0, f["credito"] or 0]
            if f.get("fx") and f["fecha"] in inicio:   # ADR-002: el importe sale de DATOS OCR
                base, fe = inicio[f["fecha"]], f["fecha"]
                imp[f["fx"][0] == "credito"] = "=" + formula(f["fx"][1], k, lambda j: ref_fila(fe, j), lambda i: f'IF({D}{DC["estado"]}{base + i}="ok",{D}{DC["valor"]}{base + i},0)')   # FIX-2: solo suma si está «ok»
            v = [date.fromisoformat(f["fecha"]), int(f["codigo"]) if str(f["codigo"]).isdigit() else (f["codigo"] or None), f["nombre"], f["tercero"], f["descripcion"],
                 *imp, None, f["reporta"] or None, f["medio"] or None]
            for i, x in enumerate(v, 1):
                c = ws.cell(k, i, x); c.border = FINO
                if i not in (6, 7): texto(c)   # F/G sí pueden ser fórmulas (ADR-002)
                c.fill = _f(VERDE if str(f["codigo"]).startswith("4") or f.get("grupo") == "venta" else ROSA)
            ws.cell(k, 1).number_format = "dd/mm/yyyy"; ws.cell(k, 1).alignment = Alignment(horizontal="center")
            for i in (6, 7): ws.cell(k, i).number_format = '$ #,##0;-$ #,##0;"$ -"'
        for i, w in enumerate([12, 14, 34, 28, 42, 17, 17, 3, 11, 18], 1): ws.column_dimensions[L(i)].width = w
        ws.freeze_panes = "A9"; ws.auto_filter.ref = f"A8:J{ult_fila}"
    rs = wb.create_sheet("RESULTADO")
    rs.append(["Mes", "Ingresos (4…)", "Gastos (5…)", "Ganancia (+) / Pérdida (−)"])
    for c in rs[1]: c.font = Font(bold=True); c.fill = _f(AZUL); c.alignment = Alignment(horizontal="center", wrap_text=True)
    for k, (nom, y, m) in enumerate(hojas, 2):
        q = f"'{nom}'!"
        rs.cell(k, 1, f"{MESES[m - 1].capitalize()} {y}")
        rs.cell(k, 2, f'=SUMIFS({q}G:G,{q}B:B,">=40000000",{q}B:B,"<50000000")-SUMIFS({q}F:F,{q}B:B,">=40000000",{q}B:B,"<50000000")')
        rs.cell(k, 3, f'=SUMIFS({q}F:F,{q}B:B,">=50000000",{q}B:B,"<70000000")-SUMIFS({q}G:G,{q}B:B,">=50000000",{q}B:B,"<70000000")')
        rs.cell(k, 4, f"=B{k}-C{k}")
        for c in (2, 3, 4): rs.cell(k, c).number_format = '$ #,##0;[Red]-$ #,##0'
    t = len(hojas) + 2
    rs.cell(t, 1, "TOTAL")
    for c in (2, 3, 4): rs.cell(t, c, f"=SUM({L(c)}2:{L(c)}{t - 1})").number_format = '$ #,##0;[Red]-$ #,##0'
    for c in rs[t]: c.font = Font(bold=True); c.fill = _f("EEF6FE")
    rs.cell(t + 2, 1, "Ojo: los insumos que compras (cocina, barra, empaques) quedan como activo y no se descuentan aquí. Para una ganancia real, resta el costo de lo consumido con el inventario final de cada mes.")
    rs.cell(t + 2, 1).alignment = Alignment(wrap_text=True, vertical="top"); rs.merge_cells(start_row=t + 2, start_column=1, end_row=t + 2, end_column=4); rs.row_dimensions[t + 2].height = 48
    for i, w in enumerate([22, 20, 20, 26], 1): rs.column_dimensions[L(i)].width = w
    if not hojas: wb.remove(rs); wb.create_sheet("MOVIMIENTOS")
    if avisos or inicio:
        av = wb.create_sheet("AVISOS"); av["A1"] = "Avisos de exportación"; av["A1"].font = Font(bold=True); av.column_dimensions["A"].width = 110
        for a in avisos + (NOTAS_DATOS if inicio else []): av.append([a]); texto(av.cell(av.max_row, 1))
    buf = io.BytesIO(); wb.save(buf); return buf.getvalue()
