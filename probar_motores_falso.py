"""Trabajador Indra falso para probar_motores.py (T2). Habla el mismo protocolo que ocr_module/indra_worker.py, sin modelo.

FALSO_MODOS = "cuelga,ok" elige el modo por arranque (el último se repite); FALSO_CONTADOR = archivo que cuenta los arranques.
  ok      responde bien (numeros → "85560 | 45.000", upright → giro 90, incl 8.0)
  eco     numeros → sha1 del png en base64 (para ver que dos hilos no mezclan respuestas)
  cuelga  saluda y no contesta ningún pedido
  muere   saluda y sale sin contestar el primer pedido
  miente  upright → giro 45, numeros → texto que no es str
  basura  contesta una línea que no es JSON
  mudo    nunca saluda
Sin FALSO_MODOS es «ok». EOF en stdin cierra, como el de verdad."""
import hashlib, json, os, sys, time


def modo():
    modos = (os.environ.get("FALSO_MODOS") or "ok").split(",")
    ruta, n = os.environ.get("FALSO_CONTADOR"), 0
    if ruta:
        try:
            with open(ruta) as f: n = int(f.read() or 0)
        except FileNotFoundError: pass
        with open(ruta, "w") as f: f.write(str(n + 1))
    return modos[min(n, len(modos) - 1)]


def responder(obj):
    sys.stdout.write((obj if isinstance(obj, str) else json.dumps(obj)) + "\n"); sys.stdout.flush()


def main():
    m = modo()
    if m == "mudo":
        time.sleep(3600); return
    responder({"ready": True, "version": "1.1.2", "load_s": 0.01})
    for raw in sys.stdin:
        if not raw.strip(): continue
        req = json.loads(raw)
        op = req.get("op")
        if op == "quit":
            responder({"bye": True}); return
        if m == "cuelga":
            time.sleep(3600); return
        if m == "muere":
            sys.exit(3)
        if m == "basura":
            responder("esto no es json"); continue
        if m == "miente":
            responder({"giro": 45, "incl": 8.0, "ms": 1.0} if op == "upright" else {"texto": 123, "ms": 1.0}); continue
        if op == "numeros":
            texto = hashlib.sha1(req["png"].encode()).hexdigest()[:12] if m == "eco" else "85560 | 45.000"
            if m == "eco": time.sleep(0.01)
            responder({"texto": texto, "ms": 1.0})
        elif op == "upright":
            responder({"giro": 90, "incl": 8.0, "ms": 1.0})
        else:
            responder({"error": f"op desconocida: {op!r}"})


if __name__ == "__main__":
    main()
