# ADR-024 · Plan B sklearn del gate N1: capa TF-IDF + regresión logística (N1 sigue en 85 %)

Estado: aceptado (2026-10-25, pedido por el usuario; reabre N2 solo para entrenar)

## Contexto
Tras ADR-023 (T5c), N1 da 67,2 % por ítem: cobertura 77 %, precisión de lo decidido 87,3 %; 4 cuentas con ≥ 10 ítems < 60 % (51355001, 13452501, 51952501, 14050502). Las palancas a mano dieron poco (bigramas +0,3, frases +0,3, terceros 0); «Recibo N» +6,9, pero el libro solo tiene sept. El usuario mantiene N1 = 85 % y pide el plan B de 01 (Q1 d).

## Opciones
1. **sklearn en la app** (pickle/joblib): instalar y auditar sklearn+scipy en cada PC; cargar pickle es ejecutar código.
2. **Entrenar con sklearn, predecir con numpy**: `herramientas/entrenar_ml.py` ajusta `TfidfVectorizer(analyzer="char_wb", ngram_range=(2,5), sublinear_tf=True)` + `LogisticRegression` y exporta vocabulario, idf, coeficientes e intercepto a JSON; el `Motor` lo aplica con numpy (ya en `requirements.txt`).
3. **Bajar N1**: descartado por el usuario.

## Decisión
Opción 2.
- **Capa «ml»** entre vecino y puente. Entra descripción + proveedor normalizados (y el texto OCR del papel cuando hay cruce «Recibo N»). Decide si `p ≥ umbral` y `p1 − p2 ≥ margen` (en `por_confirmar.json`). Si no, va a la puente; `puc_valida` sigue al final (ADR-022).
- **Modelo** `parser_module/contable/modelo_ml.json`: local y en `.gitignore`, como `terceros_cuentas.json`, porque los n-gramas pueden llevar nombres (N5). Sin archivo, la capa se apaga con aviso y el motor queda como hoy.
- **Dependencia**: `scikit-learn` fijo en `requirements-entrenar.txt` y auditado con pip-audit. Solo lo necesita el PC que entrena; la app no lo importa (N2 se mantiene para la app).
- **Paridad**: test que compara la predicción numpy con `predict_proba` de sklearn (se salta si sklearn no está).

## Medición
Igual que ADR-023: gate N1 (entrena jun–ago, prueba sept–oct) + walk-forward, barrido de `umbral` 0,30–0,80 y `margen` 0–0,20 (el más bajo con precisión decidida ≥ 90 %), y aporte de la capa «ml». Antes de integrar, un spike fuera de la app da la cifra: si el spike no llega a 85 %, se para.

## Consecuencias
+ La app no gana dependencias ni carga pickle; cada PC solo necesita copiar `modelo_ml.json`.
− Hay que reimplementar el transform char_wb en numpy y mantener la paridad. Hay que re-entrenar al sumar meses.
− Las descripciones sin palabras («Recibo 164») siguen dependiendo del cruce con el libro. Si aun así N1 < 85 %, el usuario decide en un ADR nuevo.
