# 01 · Research — extracto bancario (01c #5)  · light, 2026-10-20

## Summary
- **The format is known from the real file, not the web.** Bancolombia exports XLS with 4 columns: `Fecha | Descripción | Referencia | Valor`, where Valor is signed (− = outflow). There are no header rows before the data, and the date is a datetime. Sample: `../data/202609 - Movimientos banco 1-30Sept2026.xlsx`, sheet "Hoja 1" (513 lines, 1–23 Sept). The web has no published layout. Reading it with openpyxl (already pinned) is enough, so no new library.
- **Sheet "MOVIMIENTOS" in the same file is a hand-labelled month.** It has 643 lines for 1–30 Sept, each with a `Concepto` column (GMF, RECAUDO QR, PAGO LLAVE, ABONO VISA/MASTER/AMEX, PAGO RAPPI, RENDIMIENTOS, TRANSFER CR, TRANSFER NEQUI CR, PAGO PSE, PAGO QR, COMPRA) and monthly totals. This is the test oracle for the classifier.
- **Classification is two-level.** Level 1 is the *concepto*, found by an ordered list of anchored prefix rules over Descripción plus the sign. It is deterministic, and ≈100% of lines map this way. Level 2 is the *cuenta PUC* for outflows (nómina vs arriendo vs proveedor vs servicio). The text rarely says which: `TRANSFERENCIA CTA SUC VIRTUAL` (≈17.9 M) has no counterparty, and `TRANSFERENCIAS A NEQUI` / `TRANSF A <nombre>` (≈14.2 M) only gives a name. So the user picks the account, and the app remembers the choice by counterparty (hledger/beancount pattern).
- **Biggest risk: double counting.** Sales receipts (QR, llave, card abonos, Rappi) already enter the ledger through the hand-typed `banco` casillas. These are filled for 09-01..09-23 and turned into rows on `11200501` by `asientos.construir`. The importer must either fill those casillas from the file or skip receipt lines. It must never add both.
- **Regulated.** PUC codes are taken from the accountant's manual (53152001 GMF, 42100505 rendimientos, 5105/5120/5135…), not from the web, where the sources conflict. The open items are listed under Risks for contabilidad.

## Options compared
| Question | Option | Fit | Cost | Maturity | Verdict |
|---|---|---|---|---|---|
| Read file | openpyxl on "Hoja 1" (4 cols, signed Valor) | exact | low | high (in use) | **Pick** |
| Read file | PDF parsers (kenamal777, angelluna03030) | PDF only | med | unknown | No: we have XLS |
| Concepto | Ordered anchored-regex table in JSON (like `normalizacion.json`) | deterministic, testable vs MOVIMIENTOS | low | hledger-proven | **Pick** |
| Cuenta of outflows | Rule table + "remember my choice" per counterparty + review list (④ pattern) | handles opaque transfers | med | beancount smart_importer idea | **Pick** |
| Cuenta of outflows | ML classifier on past choices | needs history we don't have | high | medium | No (v1) |
| Cuenta of outflows | User types everything by hand (status quo, 1–23 Sept) | works | user time per month | — | Fallback |

## Codebase map
- `app.py` Flask on 127.0.0.1:5050 (`iniciar.bat`). Ledger in `datos/libro.json` (`_leer_libro`/`_guardar_libro` app.py:202-216, POST /api/contable/libro :383, `cont_importar` :549).
- `parser_module/contable/asientos.py`: `construir()` :268 → rows `fila()` :306 {fecha, codigo, nombre, tercero, descripcion, debito, credito, reporta, medio, grupo, docs, fx}. `BANCO=11200501`, `RECAUDOS_BANCO` :10-22.
- Day record: {fecha, documentos, **banco** (llave, tarjetas, qr, nequi, transferencias, pse, rappi), cierre, cruces, filas, pendientes, debito, credito}.
- PUC: `parser_module/contable/plan_de_cuentas.json` (1120 has only 11200501–04). `normalizacion.json` holds the medio/reporta maps; `terceros_cuentas.json` has no bank keys.
- UI: `static/contable.html` tabs ①–④. The review screen to reuse is `cargarRevision` (:386), GET/POST `/api/contable/revision…`.
- Tests: `python probar_contable.py` (✓/✗, ends "TODO OK"; exit code always 0), plus the other `probar_*.py`.

## Risks / unknowns
1. **Double counting** of sales receipts against the `banco` casillas (see Summary). The choice is a design decision for 2/3: fill the casillas from the file, or replace them.
2. **The same day is imported twice** (overlapping downloads 1–23 then 1–30). The importer must deduplicate. There is no unique id: Referencia is often empty or reused (`0092620968` for all QR), so the key has to be built from (fecha, descripción, referencia, valor, occurrence #).
3. **"Hoja 1" has a single date per line at 05:00** (a UTC artefact). Use the date only.
4. **Mislabels exist in the manual sheet** (`TRABSFER CR`, a Referencia typed into Concepto, the same "TRANSF A ANA PRUEBA" labelled both CR and NEQUI CR). Treat it as a guide, not perfect truth.
5. **For contabilidad to confirm:** GMF account 53152001 and whether 50% of it goes in renta; rendimientos 42100505 and any retención (135515 / 2365?); nómina 2505 vs 5105; arriendo 5120 plus retención 3.5% (base 10 UVT); servicios 5135; card abonos net of commission (ABONO NETO → comisión 530515?); Rappi settlement against the cuenta por cobrar from v1.4.0; PSE to PROVEEDOR (a platform? publicidad?).
6. **Sign of a few lines is unexpected:** credits labelled COMPRA, debits labelled VENTAS (≈8 lines). The user must review these.
7. **The empresas download can be a ZIP with a password** (the document ID). v1 assumes the user opens it and gives the .xlsx.

## Sources
- Bancolombia help, extract downloads: https://www.bancolombia.com/centro-de-ayuda/preguntas-frecuentes/descargar-extractos-bancolombia-sucursal-virtual · https://www.bancolombia.com/centro-de-ayuda/preguntas-frecuentes/descargar-extractos-sucursal-virtual-empresas
- https://github.com/kenamal777/conciliacion-bancaria
- hledger CSV rules: https://hledger.org/import-csv.html
- Beancount categorization: https://beancount.io/forum/t/smart-defaults-training-your-importers-to-categorize-like-you-would/230
- GMF: https://funcionpublica.gov.co/eva/gestornormativo/norma_pdf.php?i=41063 · https://siemprealdia.co/colombia/contabilidad/gmf-es-gasto-administrativo-o-financiero/
- Retención 1355/2365: https://www.gerencie.com/qa/cuando-se-utiliza-la-cuenta-1355-y-la-2365-931/ · arriendo 3.5%: https://cijuf.org.co/node/28277
