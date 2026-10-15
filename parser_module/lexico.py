"""Léxico de ganancia/pérdida y faltante/sobrante en cierres de caja de restaurantes (español).
Cada término lleva el SIGNO que implica: +1 ganancia/sobrante · -1 pérdida/faltante · 0 «tal como viene impreso».
Así «FALTANTE 138.950» se guarda como -138.950 aunque el recibo no traiga el signo menos."""
from __future__ import annotations
from .esquema import limpiar

# (término, signo, peso 0-1)  · peso menor = término ambiguo → el parser lo deja «por revisar»
_RESULTADO = [
    *[(t, +1, 1.0) for t in ("ganancia", "ganancias", "ganancia del dia", "ganancia neta", "ganancia diaria", "utilidad",
                              "utilidades", "utilidad del dia", "utilidad neta", "utilidad diaria", "beneficio", "beneficios",
                              "beneficio neto", "lucro", "superavit", "resultado positivo", "balance positivo")],
    *[(t, -1, 1.0) for t in ("pérdida", "pérdidas", "pérdida del día", "pérdida neta", "pérdida diaria", "déficit", "quebranto",
                              "resultado negativo", "balance negativo")],
    *[(t, 0, 1.0) for t in ("ganancia / pérdida", "ganancia o pérdida", "ganancias y pérdidas", "utilidad / pérdida",
                             "utilidad o pérdida", "pérdida / ganancia", "pérdidas y ganancias", "p y g", "pyg", "p&g",
                             "resultado del día", "resultado neto", "resultado final", "resultado diario")],
    ("resultado", 0, 0.85), ("balance", 0, 0.8), ("balance del día", 0, 0.85),
]
_DIFERENCIA = [
    *[(t, -1, 1.0) for t in ("faltante", "faltantes", "faltante de caja", "faltante en caja", "faltante caja")],
    *[(t, -1, 0.75) for t in ("falta", "faltan", "faltó")],
    *[(t, +1, 1.0) for t in ("sobrante", "sobrantes", "sobrante de caja", "sobrante en caja", "sobrante caja",
                              "excedente", "excedente de caja", "exceso de caja")],
    *[(t, +1, 0.75) for t in ("sobra", "sobran")],
    # signo desconocido: lo normal es que venga impreso (-/+); si no viene, el parser lo deja «por revisar»
    *[(t, 0, 1.0) for t in ("faltante / sobrante", "faltante o sobrante", "faltante y sobrante", "sobrante / faltante",
                             "sobrante o faltante", "sobra o falta", "falta o sobra", "diferencia", "diferencia de caja",
                             "diferencia en caja", "diferencia caja", "dif de caja", "descuadre", "descuadre de caja",
                             "cuadre", "cuadre de caja")],
]
RESULTADO = {limpiar(t): (s, p) for t, s, p in _RESULTADO}
DIFERENCIA = {limpiar(t): (s, p) for t, s, p in _DIFERENCIA}
# alias limpio → (signo, peso, ambiguo)   ambiguo = «diferencia», «descuadre»…: sin signo impreso no se sabe si falta o sobra
SIGNO = {**{a: (s, p, False) for a, (s, p) in RESULTADO.items()}, **{a: (s, p, s == 0) for a, (s, p) in DIFERENCIA.items()}}


def terminos(grupo: dict) -> list:
    return sorted(grupo)
