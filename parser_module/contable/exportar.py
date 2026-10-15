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


def libro_a_excel(dias: dict, negocio: str = "", nit: str = "") -> bytes:
    """dias: {'2026-09-12': [fila, …]} con filas de asientos.construir()."""
    wb = Workbook(); wb.remove(wb.active)
    por_mes = defaultdict(list)
    for f in sorted(dias): por_mes[f[:7]].extend(dias[f])
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
        for k, f in enumerate(sorted(filas, key=lambda x: (x["fecha"], 0)), 9):   # sorted es estable: conserva el orden de cada día
            v = [date.fromisoformat(f["fecha"]), int(f["codigo"]) if str(f["codigo"]).isdigit() else (f["codigo"] or None), f["nombre"], f["tercero"], f["descripcion"],
                 f["debito"] or 0, f["credito"] or 0, None, f["reporta"] or None, f["medio"] or None]
            for i, x in enumerate(v, 1):
                c = ws.cell(k, i, x); c.border = FINO
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
    buf = io.BytesIO(); wb.save(buf); return buf.getvalue()
