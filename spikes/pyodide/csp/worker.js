// Worker módulo: Pyodide y wheels solo desde rutas propias, sin micropip ni loadPackage de red.
import { loadPyodide } from "/pyodide/314.0.7/pyodide.mjs";

const WHEELS = ["et_xmlfile-2.0.0-py3-none-any.whl", "openpyxl-3.1.5-py2.py3-none-any.whl"];
try {
  const py = await loadPyodide({ indexURL: "/pyodide/314.0.7/" });
  postMessage({ paso: "pyodide", valor: py.version });
  postMessage({ paso: "1+1", valor: py.runPython("1+1") });
  for (const n of WHEELS) {
    const r = await fetch("/py/" + n);
    py.unpackArchive(await r.arrayBuffer(), "wheel");
  }
  const xlsx = py.runPython(`
import io, openpyxl
wb = openpyxl.Workbook(); wb.active["A1"] = 2
b = io.BytesIO(); wb.save(b); len(b.getvalue())`);
  postMessage({ paso: "openpyxl xlsx bytes", valor: xlsx });
  // La CSP debe seguir bloqueando eval y salidas dentro del Worker.
  let ev; try { (0, eval)("1"); ev = "permitido (MAL)"; } catch (e) { ev = "bloqueado " + e.name; }
  postMessage({ paso: "eval en worker", valor: ev });
  let fu; try { await fetch("https://example.com/"); fu = "salió (MAL)"; } catch (e) { fu = "bloqueado"; }
  postMessage({ paso: "fetch externo en worker", valor: fu, fin: true });
} catch (e) {
  postMessage({ error: String(e), fin: true });
}
