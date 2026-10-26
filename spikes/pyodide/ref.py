import sys, json, time; sys.path[:0] = [sys.argv[1], sys.argv[2]]
from parser_module.contable.exportar import crudo
from nucleo import libro_desde_crudo
lib = json.load(open(sys.argv[1] + "/datos/libro.json", encoding="utf8"))
b = crudo(lib, "2026-09-01", "2026-09-30"); open(sys.argv[2] + "/crudo_sept.json", "wb").write(b)
t = time.time(); x = libro_desde_crudo(b); print("cpython s", round(time.time() - t, 2), "crudo KB", len(b) // 1024, "xlsx KB", len(x) // 1024)
open(sys.argv[2] + "/ref.xlsx", "wb").write(x)
