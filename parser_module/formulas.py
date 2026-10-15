"""Fórmulas de columnas calculadas y controles: {clave} + {otra} - 2 * ({x} / {y}).
Operadores + - * /, paréntesis, números y la función si0(a, b) = «a, y si a es 0 entonces b». Una sola gramática para Python, la interfaz (JavaScript) y Excel."""
from __future__ import annotations
import re

_REF = re.compile(r"\{([a-z][a-z0-9_]*)\}")
_TOK = re.compile(r"\s*(?:(\d+(?:\.\d+)?)|\{([a-z][a-z0-9_]*)\}|(si0)(?=\s*\()|([+\-*/(),]))")


def claves_de(f: str) -> list:
    """Columnas que usa la fórmula, sin repetir y en orden de aparición."""
    return list(dict.fromkeys(_REF.findall(f or "")))


def _tokens(f: str):
    f, pos, out = (f or "").strip(), 0, []
    while pos < len(f):
        m = _TOK.match(f, pos)
        if not m:
            raise ValueError(f"Fórmula no válida cerca de «{f[pos:pos + 10].strip()}»")
        out.append(("num", float(m.group(1))) if m.group(1) else ("ref", m.group(2)) if m.group(2)
                   else ("fn", "si0") if m.group(3) else ("op", m.group(4)))
        pos = m.end()
        while pos < len(f) and f[pos].isspace(): pos += 1
    return out


def _parse(f: str):
    t, i = _tokens(f), [0]
    if not t: raise ValueError("La fórmula está vacía.")
    peek = lambda: t[i[0]] if i[0] < len(t) else (None, None)

    def eat(): i[0] += 1; return t[i[0] - 1]

    def expr():
        a = term()
        while peek() in (("op", "+"), ("op", "-")): a = ("bin", eat()[1], a, term())
        return a

    def term():
        a = factor()
        while peek() in (("op", "*"), ("op", "/")): a = ("bin", eat()[1], a, factor())
        return a

    def factor():
        k, v = peek()
        if k == "num": eat(); return ("num", v)
        if k == "ref": eat(); return ("ref", v)
        if k == "fn":
            eat()
            if peek() != ("op", "("): raise ValueError("Después de si0 va un paréntesis.")
            eat(); a = expr()
            if peek() != ("op", ","): raise ValueError("si0 necesita dos valores separados por coma: si0(a, b).")
            eat(); b = expr()
            if peek() != ("op", ")"): raise ValueError("Falta cerrar un paréntesis en la fórmula.")
            eat(); return ("fn", a, b)
        if (k, v) == ("op", "-"): eat(); return ("neg", factor())
        if (k, v) == ("op", "("):
            eat(); a = expr()
            if peek() != ("op", ")"): raise ValueError("Falta cerrar un paréntesis en la fórmula.")
            eat(); return a
        raise ValueError("La fórmula está incompleta o mal escrita.")

    a = expr()
    if i[0] != len(t): raise ValueError("Sobra algo al final de la fórmula.")
    return a


def validar(f: str, claves) -> None:
    """Lanza ValueError (con un mensaje claro) si la fórmula está mal escrita o usa columnas inexistentes."""
    _parse(f)
    faltan = [k for k in claves_de(f) if k not in set(claves)]
    if faltan:
        raise ValueError("La fórmula usa columnas que no existen: " + ", ".join(faltan))


def evaluar(f: str, valores: dict) -> float:
    """valores: {clave: número}. Lo que falte o sea None vale 0; una división por cero da 0 (igual que el Excel)."""
    def ev(n):
        if n[0] == "num": return n[1]
        if n[0] == "ref": return float(valores.get(n[1]) or 0)
        if n[0] == "neg": return -ev(n[1])
        if n[0] == "fn":
            a = ev(n[1]); return a if a != 0 else ev(n[2])
        a, b = ev(n[2]), ev(n[3])
        return a + b if n[1] == "+" else a - b if n[1] == "-" else a * b if n[1] == "*" else (a / b if b else 0.0)
    return ev(_parse(f))


def a_excel(f: str, celda) -> str:
    """celda(clave) → 'C5'. Devuelve la fórmula de Excel, sin el '='."""
    def tx(n):
        if n[0] == "num": return str(int(n[1])) if n[1] == int(n[1]) else repr(n[1])
        if n[0] == "ref": return celda(n[1])
        if n[0] == "neg": return f"(-{tx(n[1])})"
        if n[0] == "fn": return f"IF({tx(n[1])}<>0,{tx(n[1])},{tx(n[2])})"
        return f"({tx(n[2])}{n[1]}{tx(n[3])})"
    return tx(_parse(f))
