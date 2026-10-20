# Indra OCR vs the current OCR — spike, 2026-10-20

**Verdict: Indra does not replace qwen as the reader. It is a viable replacement for Tesseract as the second reader (R3): it confirms the receipt number on 79 % of receipts vs 26 %, ties on totals, and is 2× faster (see "As the second reader"). It is also clearly better at turning and straightening photos: right on every quarter turn where Tesseract gets 0–14 of 20 sheets, plus deskew up to ±45°, which the app lacks (see "Orientation").** On the fields it reads, it is as accurate as qwen, and it is about 100× faster with about 14× less RAM. But on its own it loses a quarter of the receipts, because it misreads the receipt number (it found 79 of 107 vs qwen's 90). A receipt with no number never reaches the ledger.

## What was compared

- **Set:** the fixed 20 photos / 107 reviewed sales receipts of September 2026 (`datos/referencia/google/subconjunto.json` → `referencia_2026-09.json`, frozen 2026-10-18 03:25). This is the same set as the qwen V0 report `20261018-040428`, the qwen full-loop report `20261018-120343_completo` and the Google spike.
- **Path:** the same as `medir_precision.leer_hoja_v0`: orient (`orientacion.preparar_pagina`), split into receipts (`orientacion.separar` with the count from the file name), OCR each piece, then the project's parser (`leer_texto`). Each engine is scored by the project's own `referencia.medir`, with no relectura, R3, R5 or R6. Only the OCR step changes.
- **Engines:** `indra-ocr==1.1.2` (models: HF tag `v1.1.0`, ONNX), run in an isolated venv on Python 3.14 with 4 threads. It ran fully offline after the one-time 76 MB model download (`HF_HUB_OFFLINE=1`). Tesseract 5.5.3 runs through `ocr_module` (`spa+eng`, psm 6, the app's own preprocessing). The qwen2.5vl:7b numbers come from the existing reports; it was not re-run.
- **Indra layout:** Indra returns one box per text run, so a receipt row "PLATO · 2 · 35,000" comes out as 3 lines. `filas` regroups boxes that share a row into one line joined with `|`, the shape the parser expects. `lineas` passes the raw lines through and breaks the payment fields (shown once below, then dropped).
- **`+rotulos`:** a harness-only fix, not in the app. A header line like `REC1BO #: 85366` / `REC180 a: 85337` / `RECBO e 85372` is rewritten to `RECIBO #: 85366`, because the parser's regex `recibo\s*#` is strict. Digits are left untouched. It is applied identically to Indra and Tesseract.

## Fidelity (107 receipts)

| Engine | Found | Doubtful | **Validated but wrong** | fecha | consumo | propina | efectivo | medio | NIT | Items (recall / precision) |
|---|---|---|---|---|---|---|---|---|---|---|
| qwen V0, one pass (report) | **90** | 20 | 11 | 91.1 | 92.2 | 92.2 | 91.1 | 93.3 | – | – |
| qwen full loop (app today) | **94** | 17 | 9 | 91.5 | 95.7 | 96.8 | 95.7 | 97.9 | – | – |
| **Indra `filas` + rotulos** | 79 | 22 | 8 | 89.9 | 94.9 | 92.4 | 89.9 | 91.1 | 49/52 | 70 % / 78 % |
| Indra `filas`, raw | 54 | 15 | 3 | 96.3 | 94.4 | 94.4 | 88.9 | 88.9 | 37/38 | 67 % / 71 % |
| Indra `lineas` + rotulos | 79 | 43 | 19 | 89.9 | 65.8 | 65.8 | 76.0 | 46.8 | 49/52 | 70 % / 75 % |
| Tesseract + rotulos | 57 | 25 | 6 | 82.5 | 94.7 | 86.0 | 78.9 | 78.9 | 38/40 | 55 % / 65 % |
| Tesseract, raw | 38 | 14 | 4 | 89.5 | 100 | 86.8 | 84.2 | 84.2 | 25/26 | 57 % / 72 % |
| Google Vision (spike, report) | 77 | 39 | 22 | 89.6 | 70.1 | 66.2 | 76.6 | 49.4 | – | – |

Field columns are % correct among the receipts that engine found (the app's metric). **Found** and **validated but wrong** (a silent error: no warning, wrong value) matter most. The other fields (domicilio, descuento, cortesía, tarjeta, transf, crédito) sit at 90–100 % for every engine except `lineas`/Google; see `spikes/indra_ocr/resultados/`.

- **Why receipts go missing** (all engines: cause = "número"):
  - With Indra, 15 of the 28 misses have no number found at all.
  - The rest are digit misreads, mostly 8→6 (`65372` for 85372, `65340` for 85340).
  - The app's R5 (numbers from the file name) or a looser number regex would recover many of these. That is app work, not measured here.
- **NIT, items:** the reference only has field-level ground truth for the amounts/date/payment method. NIT and items are scored against the reviewed receipt's stored text. An item counts as a hit when its price matches; descriptions are ignored. That text is qwen's own output, so qwen is not scored on these columns (it would grade itself). NIT is easy for everyone (≥ 94 %). On items, Indra beats Tesseract (70 % vs 55 % recall).

## Speed and memory (this PC: Windows 11, 12 logical CPUs, no GPU)

| Engine | OCR s / photo (6 receipts) | incl. orient+split | Peak RAM of the OCR process |
|---|---|---|---|
| **Indra** (4 threads) | **0.70** (≈ 0.12 s / receipt) | 1.27 | **440 MB** (model load 0.9 s) |
| Tesseract | 4.86 | 5.43 | 66 MB per call (polled), + 104 MB in the Python process |
| qwen2.5vl:7b (Ollama) | ≈ 90–110 (V1–V3 runs: 29–37 min per 20 photos) | – | ≥ 6 GB (Q4_K_M model file 6.0 GB; not measured) |

Per 100 photos: ≈ 2 min with Indra, ≈ 9 min with Tesseract and ≈ 2.5–3 h with qwen.

## As the second reader (R3): Tesseract-dígitos vs Indra (`spikes/indra_ocr/r3.py`)

Today R3b checks two values of qwen's reading against the second reader's set of numbers on the same crop: the **receipt number** and the **total** (consumo + domicilio + propina). A value the reader doesn't see becomes a soft note «Sin confirmar por segundo lector». The receipt is marked doubtful only if the reader sees *another* number from the file name and not this one. Both readers ran on the same 120 crops: Tesseract as the app runs it (`numeros_tesseract`: eng, psm 6, whitelist `0-9.,$`), and Indra's full text reduced to integers with the same `_enteros`. 103 of 107 receipts matched a crop; each crop was matched by the union of both readers' sets, so neither reader is favoured. The qwen mistakes are its 11 wrong totals on this set in the V0 and full-loop reports.

| Per receipt (103) | Tesseract-dígitos | Indra |
|---|---|---|
| Confirms the true receipt number | 27 (26 %) | **81 (79 %)** |
| Confirms the true total | 96 | 97 |
| Catches a qwen total error (true seen, wrong not seen), of 11 | 6 | 6 |
| Confirms a qwen error (the wrong value is in its set), of 11 | 5 | 5 |
| Wrongly marks a correct receipt doubtful (R3b rule) | 0 | 3 |
| Time per crop | 0.22 s | **0.11 s** |
| Numbers seen per crop | 17.8 | 22.5 |

- **The receipt-number check barely works with Tesseract today.** It doesn't see the right number on 3 of 4 receipts, so R3b leaves a false «Sin confirmar» note on ≈ 76 of 103 receipts and its doubtful rule almost never has anything to compare. Indra makes the number check real: false notes drop to ≈ 22.
- **On totals they tie.** They confirm and catch exactly the same qwen mistakes. The 5 they both miss are wrong totals that are also printed on the receipt (the same digits appear as another amount), so no second reader catches them by set membership.
- **Indra's cost: 3 false doubtfuls.** On 3 correct receipts it saw another receipt number from the file name and not the right one (a digit misread such as 8→6, or the next receipt's header at the edge of the crop). With Tesseract it's 0, but only because it rarely sees a receipt number at all. Those 3 go to ④ review; they aren't lost.

**Verdict for R3: Indra is viable as the replacement and better on the receipt number, equal on totals, 2× faster.** Its price is 3 extra doubtfuls per ≈ 100 receipts and the operational cost below.

## Orientation: turned and tilted photos (`spikes/indra_ocr/giro.py`)

Today the app straightens a sheet with Tesseract's orientation detection on the whole sheet (`orientacion.giro_automatico`, `preparar_pagina`). It handles quarter turns only, applies a turn only when confidence ≥ 0.8, and has **no deskew**. Indra's `upright()` does quarter turns with `orient.onnx` plus deskew up to ±45°.

Test: the 20 sheets, made upright as the app does, were rotated counter-clockwise by 12 angles with a white fill, giving 240 cases. Each case was oriented by each method and then went through the same steps: `recortar` → `separar` (expected count from the file name) → a reader on each crop. Score: how many of the 107 true receipt numbers / totals the reader sees. It ran with two readers, because Indra as a reader straightens each crop by itself, which hides the app's missing deskew. Tesseract-dígitos does not straighten, and neither does qwen, the app's real reader.

| Angle | Quarter turn right, app / Indra (of 20) | Totals seen, Tesseract reader: app / Indra | Totals seen, Indra reader: app / Indra | Tilt left after the step: app / Indra |
|---|---|---|---|---|
| 0° | 20 / 18* | 100 / 100 | 101 / 101 | 0 / 0 |
| 90° | 14 / 18* | 88 / 100 | 89 / 101 | 0 / 0 |
| 180° | **7** / 18* | 35 / 100 | 36 / 101 | 0 / 0 |
| 270° | 10 / 18* | 76 / 100 | 77 / 101 | 0 / 0 |
| +4° | 18 / 18* | 86 / 100 | 90 / 100 | 4° / ≤ 0.9° |
| −8° | 19 / 18* | 73 / 100 | 83 / 100 | 8° / ≤ 0.9° |
| +15° | 17 / 18* | **14** / 100 | 80 / 101 | 15° / ≤ 0.9° |
| −25° | 14 / 18* | **1** / 100 | 70 / 100 | 25° / ≤ 0.9° |
| +40° | 19 / 18* | 1 / 100 | 84 / 100 | 40° / ≤ 0.9° |
| 100° (turn + 10°) | **2** / 18* | 15 / 101 | 16 / 101 | 10° / ≤ 0.9° |
| 200° (turn + 20°) | **3** / 18* | 1 / 100 | 17 / 101 | 20° / ≤ 0.9° |
| −80° (turn − 10°) | **0** / 18* | 11 / 101 | 12 / 101 | 10° / ≤ 0.9° |

\* The other 2 sheets (`12/…85524…`, `13/…85560…`) have their receipts lying sideways on the page. Indra turns those sheets so the text is upright, Tesseract leaves them as they are, and both read the same afterwards. So it's a different choice, not an error: in effect, 20/20 at every angle.

- **Quarter turns:** Tesseract's orientation detection fails often on these receipt sheets. It gets 14/20 at 90°, 7/20 at 180° and 10/20 at 270°; mostly its confidence falls under 0.8 and the sheet is left turned. Turned *and* tilted, it gets 0–3/20. Indra turns every sheet correctly at every angle.
- **Tilt:** with no deskew, the app passes the full tilt on to the reader. A reader that doesn't straighten (Tesseract-dígitos) drops from 100 totals to 73 at 8° and to ≈ 1 from 25° on. After Indra's `upright()` the leftover tilt is ≤ 0.9° and the totals stay at 100–101 at every angle, whichever reader follows.
- **Speed:** Indra's orientation step takes 0.17–0.29 s per sheet; Tesseract's takes 0.45–0.77 s.
- **Not covered:**
  - The rotations are synthetic: a white fill, no perspective, no background. Real phone photos on a wooden table are a separate problem (`separar`), not tested here.
  - qwen was not run on tilted crops; a VLM may tolerate a few degrees better than Tesseract. Today's real scans are mostly upright, so this is about robustness to bad photos, not about the current September set.

**Verdict for orientation: Indra's `upright()` is clearly better than the app's Tesseract step.** It is right on every quarter turn where Tesseract gets 0–14 of 20, and it straightens tilts up to ±45°, which the app can't do at all. It would replace `giro_automatico` inside `preparar_pagina`, under the same constraint as R3: the 3.14 worker.

## Recommendation

1. **Keep qwen as the main reader.** Indra would lose ≈ 10 more receipts per 107 even with the label fix, and its field accuracy only ties qwen's.
2. **Replace Tesseract-dígitos with Indra in R3** (measured above: much better on the receipt number, equal on totals). This is app work, so it belongs in an sdlc cycle:
   - `numeros_tesseract` gets an Indra counterpart behind the same `leer_digitos` hook, and Tesseract stays as the fallback when Indra is missing.
   - **Blocker:** the app runs on Python 3.15, and `onnxruntime` 1.31 only ships Windows wheels up to cp314. So Indra has to run as a separate worker process in its own 3.14 venv (as `indra_worker.py` does here) until onnxruntime ships cp315.
   - The same cycle can replace the orientation step: Indra's `upright()` instead of Tesseract's orientation detection in `preparar_pagina`, which also adds the deskew the app lacks (see "Orientation"). With both changes, Tesseract would only remain as the fallback.
3. **Caveats before any adoption:**
   - The repo is one week old with one maintainer.
   - The weights carry a modified OpenRAIL-M license. It is free under US$20M revenue or funding and forbids competing with Datalab's API.
   - Windows is officially untested, though it ran fine here.
   - Pin `indra-ocr==1.1.2` and its model tag, ship the 76 MB models with `INDRA_OCR_MODEL_DIR`, and set `HF_HUB_OFFLINE=1` so it never touches the network.

## Reproduce

The harness is in `spikes/indra_ocr/`: `indra_worker.py` runs inside the isolated venv, the other two run with the project's Python. It writes only into `spikes/indra_ocr/resultados/`, never into `datos/`. Like `medir_precision`, it prints one line per photo and checkpoints, so a cut run resumes with the same command.

```bash
py -3.14 -m venv spikes/indra_ocr/indra_venv
```
```bash
spikes/indra_ocr/indra_venv/Scripts/python.exe -m pip install --only-binary=:all: "indra-ocr==1.1.2"
```
```bash
python spikes/indra_ocr/comparar.py indra-filas+rotulos
```

R3 test: `python spikes/indra_ocr/r3.py`. Orientation test: `python spikes/indra_ocr/giro.py indra` and `python spikes/indra_ocr/giro.py tesseract` (the crop reader). Set `INDRA_VENV` if the venv is elsewhere. Other motors: `indra-filas`, `indra-lineas+rotulos`, `tesseract`, `tesseract+rotulos`. The first Indra run downloads the models into `~/.cache/huggingface`; after that, set `HF_HUB_OFFLINE=1`.
