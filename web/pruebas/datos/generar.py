"""Datos de prueba SINTÉTICOS del modo contador web (el repo es público: nada real aquí).
`crudo_v1.json` = contrato R5: se generó una vez con v1.9.1 y queda fijo; solo se rehace a propósito con `--crudo`.
`extracto.xlsx` se ignora en git (*.xlsx): se rehace con `python web/pruebas/datos/generar.py` y probar_libro.py lo arma en memoria."""
import datetime as dt, io, json, sys
from pathlib import Path

AQUI = Path(__file__).parent
sys.path.insert(0, str(AQUI.parents[2]))
from parser_module.contable import leer_texto, libro
from parser_module.contable.asientos import construir
from parser_module.contable.exportar import crudo
from parser_module.contable.ejemplos import FOTO_PAPELES, VENTA

AHORA = "2026-10-01T08:00:00"


def _cmd(n, pago, extra=""):
    return "\n".join(["SU RESTAURANTE", f"RECIBO #: {n}", "Fecha de Venta: 16/09/2026 9:00:00 p. m.", extra + "SUBTOTAL CONSUMO $40,000", "**TOTAL CONSUMO>> $50000",
                      "DESCUENTO $10,000", "*TOTAL A PAGAR> $40,000", "PROPINA $", "PAGADO $40,000", pago, "CAMBIO $"])


def libro_sintetico() -> dict:
    "Dos días de prueba: 12-09 (gastos de caja, factura por transferencia, venta mixta) y 16-09 (VISA, transferencia, Nequi, Rappi, fiado + cierre)."
    dias = {"2026-09-12": (leer_texto(FOTO_PAPELES) + leer_texto(VENTA), {}, {}),
            "2026-09-16": ([leer_texto(_cmd(90001 + i, p, x))[0] for i, (p, x) in enumerate([("PAGA CON VISA $40,000", ""), ("PAGA CON TRANSFEREN", ""),
             ("PAGA CON NEQUI $40,0", ""), ("PAGA CON RAPPI $40,000", ""), ("PAGA CON CRED.PERSONA $40,000", "Cliente: ANA PRUEBA\n")])], {"qr": 0}, {"total_vendido": 200000})}
    lib = {}
    for f, (docs, banco, cierre) in dias.items():
        r = construir(f, docs, banco, libro.cfg(), cierre)
        lib[f] = libro.dia(f, r, banco, cierre, None, AHORA)
    return lib


def crudo_v1() -> bytes:
    j = json.loads(crudo(libro_sintetico()))
    j["exportado"] = AHORA   # fijo: la sha256 cubre solo «dias»
    return json.dumps(j, ensure_ascii=False, indent=1).encode("utf-8")


FILAS_EXTRACTO = [(dt.datetime(2026, 9, 12), "PAGO LLAVE SEBASTIAN HERNANDEZ", "", 10000),
                  (dt.datetime(2026, 9, 12), "IMPTO GOBIERNO 4X1000", "", -40),
                  (dt.datetime(2026, 9, 16), "ABONO NETO VISA", "123", 38500),
                  (dt.datetime(2026, 9, 16), "PAGO INTERBANC RAPPI SAS", "", 40000),
                  (dt.datetime(2026, 9, 18), "PAGO PSE PROVEEDOR EJEMPLO SAS", "", -120000),   # día que el crudo no trae: lo crea
                  (dt.datetime(2026, 9, 30), "ABONO INTERESES AHORROS", "", 321)]


def extracto_xlsx(filas=FILAS_EXTRACTO) -> bytes:
    from openpyxl import Workbook
    wb = Workbook(); ws = wb.active; ws.title = "Hoja 1"; ws.append(["Fecha", "Descripción", "Referencia", "Valor"])
    for f in filas: ws.append(list(f))
    b = io.BytesIO(); wb.save(b); return b.getvalue()


if __name__ == "__main__":
    if "--crudo" in sys.argv or not (AQUI / "crudo_v1.json").exists():
        (AQUI / "crudo_v1.json").write_bytes(crudo_v1()); print("crudo_v1.json escrito")
    (AQUI / "extracto.xlsx").write_bytes(extracto_xlsx()); print("extracto.xlsx escrito")
