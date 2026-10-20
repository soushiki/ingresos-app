"""Vocabulario de medio de pago (01c #8, T1): cada sinónimo → uno de los 8 medios; desconocido → vacío + aviso; nunca inventa."""
import json
from pathlib import Path
from parser_module.contable import documentos as D

fallos = []
def chk(cond, msg):
    print(("✓ " if cond else "✗ ") + msg)
    if not cond: fallos.append(msg)

CANON = {"Efectivo", "Transferencia", "Tarjeta", "QR", "Bre-B", "PSE", "App", "Crédito personal"}
chk(set(D.MEDIOS_CANON) == CANON and len(D.MEDIOS_CANON) == 8, "MEDIOS_CANON tiene los 8 medios")

# cada sinónimo del mapa (normalizacion.json) cae en un medio canónico
mapa = json.loads((Path(D.__file__).parent / "normalizacion.json").read_text(encoding="utf8"))["medio_canonico"]
chk(bool(mapa) and set(mapa.values()) <= CANON, "el mapa del json solo apunta a los 8")
for k, esperado in mapa.items():
    m, aviso = D.medio_canonico(k)
    chk(m == esperado and not aviso, f"«{k}» → {esperado} (dio {m!r})")

for txt, esp in [("Nequi", "Transferencia"), ("Daviplata", "Transferencia"), ("transf", "Transferencia"), ("Consignación", "Transferencia"),
                 ("Datáfono", "Tarjeta"), ("VISA", "Tarjeta"), ("débito", "Tarjeta"), ("Crédito tarjeta", "Tarjeta"),
                 ("Rappi", "App"), ("llave", "Bre-B"), ("Bre-B", "Bre-B"), ("Efectivo", "Efectivo"), ("QR", "QR"), ("PSE", "PSE"),
                 ("Crédito personal", "Crédito personal"), ("Tarjeta", "Tarjeta"), ("App", "App")]:
    chk(D.medio_canonico(txt) == (esp, ""), f"«{txt}» → {esp}")

for txt in ["(sin medio)", "", None, "Bitcoin", "Mixto", "xyz123"]:
    m, aviso = D.medio_canonico(txt)
    chk(m == "" and (aviso or txt in ("", None, "(sin medio)")), f"«{txt}» → vacío" + (" + aviso" if aviso else ""))
chk(D.medio_canonico("Bitcoin")[1] != "" and D.medio_canonico("Mixto")[1] != "", "desconocido y «Mixto» traen aviso")
chk(D.medio_canonico("(sin medio)")[0] == "" and D.medio_canonico("")[0] == "", "«(sin medio)» y vacío no inventan")

# _medio devuelve el canónico; el crudo queda en medio_detalle
chk(D._medio("Pago: Nequi") == "Transferencia", "_medio: Nequi → Transferencia")
chk(D._medio_crudo("Pago: Nequi") == "Nequi", "_medio_crudo conserva «Nequi»")
chk(D._medio("Visa débito") == "Tarjeta" and D._medio("nada que ver aquí") == "", "_medio: visa → Tarjeta; sin medio → vacío")
fac = D.interpretar("Factura de venta 123\nProveedor X SAS\nMétodo de pago: Daviplata\nTotal 50.000") if hasattr(D, "interpretar") else None
if fac:
    d = fac[0] if isinstance(fac, list) else fac
    chk(d["medio"] == "Transferencia" and d["medio_detalle"] == "Daviplata", f"factura: medio Transferencia, detalle Daviplata ({d['medio']}/{d.get('medio_detalle')})")

print(f"\n{len(fallos)} fallos" if fallos else "\nTODO OK")
raise SystemExit(1 if fallos else 0)
